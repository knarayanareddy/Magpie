"""DECIDE — comps-first pricing + gate (oracle) + trust tier. Models propose; code decides (Art V)."""
from __future__ import annotations
import re, sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skin"))
import policy as skin  # the oracle — n8n node must mirror skin/policy.py (Art II.4)

from . import config, rerank

ADVANCE_FEE_RE = re.compile(
    r"(iban|nl\d{2}[A-Z]{4}\d{4,}|tikkie|paypal\.me|pay (in advance|to reserve)|transfer €?\d+)", re.I)


@dataclass
class Decision:
    listing_id: str
    action: str                    # pursue | escalate | skip
    reasons: list[str] = field(default_factory=list)
    tier: str = "T2"
    facts: dict = field(default_factory=dict)
    gate: str = "v0"


def facts_for(item: dict, comps: dict) -> dict:
    key = _comps_key(item["title"], comps)
    c = comps.get(key, {}) if key else {}
    mz = skin.margin_z(item.get("price_eur"), c.get("median"), c.get("mad"))
    return {
        "margin_z": mz,
        "comps": c or None,                       # None => fail closed: no_comps
        "duplicate_photo": float(item.get("duplicate_photo") or 0.0),
        "offplatform_payment_request": bool(ADVANCE_FEE_RE.search(item.get("description", ""))),
        "text": (item.get("title", "") + " " + item.get("description", ""))[:2000],
        "is_mine": bool(item.get("is_mine", False)),
    }


def decide(item: dict, facts: dict, gate: str = "v0") -> Decision:
    if gate == "v0":
        res = skin.gate_v0(facts)                       # 3 rules, zero models (M0 legal gate)
    else:
        res = skin.gate_v1(item.get("judge_answers"), facts)
    tier = "T1" if facts.get("is_mine") else config.tier_for(item.get("category", "other"))
    if item.get("price_eur", 0) > config.DEAL_EUR_AUTO_CEILING:
        tier = "T3"
    return Decision(item["id"], res.action.value, list(res.reason_codes), tier, facts, gate)


def _comps_key(title: str, comps: dict) -> str | None:
    t = (title or "").lower()
    for k in sorted(comps, key=len, reverse=True):
        if k in t:
            return k
    return None
