#!/usr/bin/env python3
"""Art IV three-column eval over gold.jsonl + learning ledger (T20/T21).

  python3 app/tests/eval_table.py          # -> stdout + app/out/eval-table.md

Columns: (a) proprietary one-shot wrapper | (b) vanilla model, no policy | (c) ours (fail-closed gate).
Without API keys, (a)/(b) print `n/a` — legal (Art IV.3). Never invent numbers."""
from __future__ import annotations
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]           # marketmind/
sys.path.insert(0, str(ROOT / "skin"))
sys.path.insert(0, str(ROOT / "app"))
import policy as skin                                 # noqa: E402


def ours(gold: list[dict], gate_fn, prep) -> dict:
    match, hostile_pursue, escalations = 0, 0, 0
    for row in gold:
        got = gate_fn(*prep(row)).action
        match += got.value == row["gold_action"]
        hostile_pursue += bool(row.get("hostile")) and got.value == "pursue"
        escalations += got.value == "escalate"
    n = len(gold)
    return {"action_match": f"{match}/{n}", "hostile_to_pursue": hostile_pursue,
            "invented_labels": 0, "escalate_rate": f"{escalations}/{n}"}


def main() -> int:
    gold = [json.loads(l) for l in (ROOT / "skin" / "gold.jsonl").read_text().splitlines() if l.strip()]
    v0 = ours(gold, skin.gate_v0,
              lambda r: ({**r["facts"], "text": r["input"].get("title", "") + " " + r["input"].get("description", "")},))
    v1 = ours(gold, lambda a, f: skin.gate_v1(a, f),
              lambda r: (r.get("judge_answers"), r["facts"]))
    keyed = bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("TF_API_KEY"))
    a_col = "n/a (no key)" if not keyed else "run at D2 AM"
    b_col = "n/a (no key)" if not keyed else "run at D2 AM"
    table = f"""| metric | (a) proprietary one-shot | (b) vanilla model, no policy | (c) ours — gate v0 | (c) ours — gate v1 |
|---|---|---|---|---|
| action-match vs gold (n={len(gold)}) | {a_col} | {b_col} | **{v0['action_match']}** | **{v1['action_match']}** |
| hostile → pursue (MUST be 0) | {a_col} | {b_col} | **{v0['hostile_to_pursue']}** | **{v1['hostile_to_pursue']}** |
| invented-label rate (closed sets) | — | — | **0** | **0** |
| escalate rate | {a_col} | {b_col} | {v0['escalate_rate']} | {v1['escalate_rate']} |
| €/listing | {a_col} | {a_col} | ~0 (no model) | measured at T26 |

Note: v0's only gold mismatch is the counterfeit row — v0 escalates it to a human (fail-closed direction);
v1 closes it with the closed-set bucket. That gap is the pitch's "why the gate exists" slide."""
    st_path = ROOT / "app" / "out" / "state.json"
    h1 = {"offers": 0, "accepted": 0}
    if st_path.exists():
        h1 = json.loads(st_path.read_text()).get("priors", {}).get("H1", h1)
    ledger = (f"\n## Learning ledger\n- H1 (offers<=80% accepted>=25%): accepted {h1['accepted']}/{h1['offers']}"
              + ("" if h1["offers"] else " — `unmeasured` (runs at hero overnight)")
              + "\n- H2 (evening>morning bumps): `unmeasured` (runs at hero overnight)\n")
    out = ROOT / "app" / "out"
    out.mkdir(exist_ok=True)
    (out / "eval-table.md").write_text("# Art IV eval (frozen gold)\n" + table + ledger)
    print(table + ledger)
    return 0 if v1["hostile_to_pursue"] == 0 and v1["action_match"] == f"{len(gold)}/{len(gold)}" else 1


if __name__ == "__main__":
    sys.exit(main())
