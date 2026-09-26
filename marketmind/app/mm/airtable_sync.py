"""Receipts -> Airtable (T18, live mode). Degrades to out/receipts.jsonl (Art VII.1: rows acceptable, never no log)."""
from __future__ import annotations
import json, os, urllib.request

FIELDS = ["receipt_id", "ts", "input_hash", "listing_id", "action_state", "reason_codes",
          "policy_branch", "tier", "actor", "hostile"]


def push(rows: list[dict]) -> dict:
    pat = os.environ.get("AIRTABLE_PAT", "")
    if not pat:
        return {"synced": 0, "note": "no AIRTABLE_PAT — rows live in receipts.jsonl (Art VII.1 degradation)"}
    base, table = os.environ["AIRTABLE_BASE"], os.environ.get("AIRTABLE_TABLE", "receipts")
    ok = 0
    for row in rows:
        fields = {k: (",".join(row.get(k, []) or []) if isinstance(row.get(k), list)
                      else (bool(row.get(k)) if k == "hostile" else row.get(k, "")))
                  for k in FIELDS}
        body = json.dumps({"records": [{"fields": fields}]}).encode()
        req = urllib.request.Request(f"https://api.airtable.com/v0/{base}/{table}", data=body,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {pat}"})
        try:
            urllib.request.urlopen(req, timeout=30)
            ok += 1
        except Exception:
            pass  # row remains in jsonl — the log never disappears
    return {"synced": ok, "of": len(rows)}
