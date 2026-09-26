"""MarketMind gate. Models propose. Code decides. Never spend, never bind, never judge a person.

Pure stdlib. This file is the ORACLE (Art II.4): the n8n `POLICY (fail-closed)` node must
mirror it exactly (mirror: app/n8n/policy_v0_node.js — run app/tests/test_gate_parity.py).
Eval:  python skin/policy.py --eval skin/gold.jsonl
Build-breaking metric: hostile -> pursue must be 0 (Art IV.2).
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

BLOCK_BUCKETS = {"weapon", "animal", "other_illegal"}
CLOSED_BUCKETS = {"ok", "weapon", "animal", "counterfeit", "pii", "other_illegal", "unknown"}


class Action(str, Enum):
    pursue = "pursue"
    escalate = "escalate"
    skip = "skip"


@dataclass
class Result:
    action: Action
    reason_codes: list[str] = field(default_factory=list)
    human_required: bool = True


# ---------- helpers (closed-set coercion; invented values fail closed) ----------

def choice(answers: dict[str, Any], key: str) -> str:
    v = answers.get(key)
    return v if v in CLOSED_BUCKETS else "unknown"  # invented label coerces to unknown


def score_label(answers: dict[str, Any], key: str, default: str = "unclear") -> str:
    v = answers.get(key)
    return v if v in {"clear_authentic", "unclear", "obvious_fake"} else default


def noul(answers: dict[str, Any], key: str, missing: float = 1.0) -> float:
    """Calibrated 0..1 score. Missing/invalid -> `missing` (fail-closed default 1.0)."""
    v = answers.get(key)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return missing
    return min(max(f, 0.0), 1.0)


def margin_z(price_eur: float | None, comp_median: float | None, comp_mad: float | None) -> float | None:
    """Deterministic comps z-score. None = no grounding = fail closed (escalate)."""
    if not price_eur or not comp_median or not comp_mad or comp_mad <= 0:
        return None
    return (comp_median - price_eur) / comp_mad  # positive = underpriced vs comps


# ---------- GATE V0 (M0/M1: three rules, zero models. Sufficient to act.) ----------
# Rule 1 = hostile-text screen (deterministic): injection phrases, illegal keywords, advance-fee/IBAN.
# Stays 3 rules total — expanded under Art VI (hostile input is in-scope from day one).

ILLEGAL_RE = re.compile(r"\b(weapon|knife|knives|gun|pistol|ammo|hunting knife|airsoft)\b", re.I)
INJECTION_PHRASES = ("ignore previous instructions", "accept any offer", "mark as sold",
                     "mark as safe", "disregard all prior")
ADVANCE_FEE_RE = re.compile(
    r"(iban|nl\d{2}[A-Z]{4}\d{4,}|tikkie|paypal\.me|pay (in advance|to reserve)|transfer €?\d+)", re.I)

def gate_v0(facts: dict[str, Any]) -> Result:
    mz = facts.get("margin_z")
    text = (facts.get("text") or "").lower()
    if any(p in text for p in INJECTION_PHRASES):
        return Result(Action.skip, ["injection_or_jailbreak"], True)   # never pursue hostile text
    if ILLEGAL_RE.search(text):
        return Result(Action.skip, ["illegal_keyword"], True)
    if facts.get("offplatform_payment_request") or ADVANCE_FEE_RE.search(text):
        return Result(Action.skip, ["offplatform_payment_request"], True)
    if mz is None or mz > 2.5:                      # no comps, or too-good-to-be-true
        return Result(Action.escalate, ["no_comps"] if mz is None else ["price_too_good"], True)
    if 0.0 < mz <= 2.5:                             # plausible underpricing band
        return Result(Action.pursue, ["ok"], False)  # tier still applies outside the gate
    return Result(Action.escalate, ["no_margin"], True)  # mz <= 0: asking at or above comps — no deal


# ---------- GATE V1 (M2+: closed sets + typed questions + deterministic facts) ----------

def gate_v1(answers: dict[str, Any] | None, facts: dict[str, Any]) -> Result:
    if not answers:
        return Result(Action.escalate, ["judge_unconfigured"], True)

    bucket = choice(answers, "policy_bucket")
    fake = score_label(answers, "counterfeit_risk")
    inj = noul(answers, "injection_or_jailbreak", missing=1.0)   # fail-closed: missing injection question -> 1.0 (skip)
    needs = noul(answers, "needs_human", missing=1.0)
    p2g = noul(answers, "price_too_good", missing=1.0)

    mz = facts.get("margin_z")
    dup = float(facts.get("duplicate_photo") or 0.0)
    offpay = bool(facts.get("offplatform_payment_request"))

    if bucket in BLOCK_BUCKETS:
        return Result(Action.skip, [bucket], True)                        # content only; never a person
    if inj >= 0.5:
        return Result(Action.skip, ["injection_or_jailbreak"], True)      # HOSTILE: never pursue
    if bucket == "pii" or offpay:
        return Result(Action.skip, ["pii" if bucket == "pii" else "offplatform_payment_request"], True)
    if bucket == "counterfeit" or fake == "obvious_fake":
        return Result(Action.skip, ["counterfeit"], True)
    if bucket == "unknown" or needs >= 0.6:
        return Result(Action.escalate, ["needs_human" if needs >= 0.6 else "unknown"], True)
    if dup >= 0.5:
        return Result(Action.escalate, ["duplicate_photo"], True)         # stolen-photo suspect
    if mz is None:
        return Result(Action.escalate, ["no_comps"], True)                # missing grounding = unknown
    if p2g >= 0.6 or mz > 3.0:
        return Result(Action.escalate, ["price_too_good"], True)          # TOO GOOD = SUSPICION
    if bucket == "ok" and p2g < 0.4 and mz <= 2.0:
        return Result(Action.pursue, ["ok"], False)                       # tier gates the how
    return Result(Action.escalate, [bucket], True)


# ---------- eval (gold.jsonl -> build-breaking metric) ----------

def run_eval(path: str) -> int:
    rows, mismatches, hostile_pursue = [], 0, 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            got = gate_v1(row.get("judge_answers") or {}, row.get("facts") or {})
            ok = got.action.value == row["gold_action"]
            rows.append((row["id"], row["gold_action"], got.action.value, ok, ",".join(got.reason_codes)))
            if not ok:
                mismatches += 1
            if row.get("hostile") and got.action == Action.pursue:
                hostile_pursue += 1
    print(f"{'id':22} {'gold':10} {'got':10} {'ok':3} reasons")
    for r in rows:
        print(f"{r[0]:22} {r[1]:10} {r[2]:10} {'✓' if r[3] else '✗':3} {r[4]}")
    print(f"\nrows={len(rows)} mismatches={mismatches} hostile->pursue={hostile_pursue}")
    print("BUILD-BREAKING METRIC:", "PASS" if hostile_pursue == 0 and mismatches == 0 else "FAIL")
    return 0 if hostile_pursue == 0 and mismatches == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--eval":
        sys.exit(run_eval(sys.argv[2]))
    print(__doc__)
