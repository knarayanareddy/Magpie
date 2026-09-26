"""RECEIPTS — every decision is logged with a hash chain (Art VII.1). Append-only; Airtable when keyed.

Chain: each row carries prev_hash -> row_hash (sha256 truncated to 16 hex). Appending continues
the chain from the last row on disk, so evidence from the hero overnight cannot be quietly rewritten
(audit C5: the previous write() truncated the file each run)."""
from __future__ import annotations
import hashlib, json, time, uuid
from pathlib import Path

GENESIS = "genesis"


def begin(item: dict) -> dict:
    payload = json.dumps(item, sort_keys=True, ensure_ascii=False)
    return {"receipt_id": str(uuid.uuid4()), "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "input_hash": hashlib.sha256(payload.encode()).hexdigest()[:16],
            "listing_id": item["id"], "actor": "agent",
            "hostile": bool(item.get("hostile", False))}
            # actor=human is set on override (Art VII.1)


def commit(r: dict, action: str, reasons: list[str], state: str, tier: str, gate: str,
           scores: dict | None = None, policy_branch: str | None = None) -> dict:
    row = {**r, "policy_branch": policy_branch or f"gate_{gate}:{action}", "action_state": state, "tier": tier,
           "reason_codes": reasons, "scores": scores or {},
           "action_state_note": "drafted != sent (Art VII.2)" if state == "drafted" else ""}
    return row


def _row_hash(body: dict) -> str:
    payload = json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def write(path, rows: list[dict]) -> None:
    """Append-only, hash-chained. Returns nothing; raises nothing on partial evidence (caller logs)."""
    p = Path(path)
    prev = GENESIS
    if p.exists():
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if lines:
            try:
                prev = json.loads(lines[-1]).get("row_hash", GENESIS)
            except Exception:
                prev = GENESIS
    with open(p, "a", encoding="utf-8") as fh:
        for row in rows:
            body = {**row, "prev_hash": prev}
            body["row_hash"] = _row_hash(body)
            fh.write(json.dumps(body, ensure_ascii=False) + "\n")
            prev = body["row_hash"]


def verify_chain(path) -> tuple[bool, str]:
    """Recompute the chain over an on-disk log. Used in selftest + judge Q&A (tamper check)."""
    prev = GENESIS
    for i, ln in enumerate(Path(path).read_text(encoding="utf-8").splitlines()):
        if not ln.strip():
            continue
        try:
            row = json.loads(ln)
        except Exception:
            return False, f"line {i+1}: unparseable"
        h = row.get("row_hash", "")
        if row.get("prev_hash", GENESIS) != prev:
            return False, f"line {i+1}: prev_hash mismatch"
        if _row_hash({k: v for k, v in row.items() if k != "row_hash"}) != h:
            return False, f"line {i+1}: row_hash mismatch (edited?)"
        prev = h
    return True, "chain intact"
