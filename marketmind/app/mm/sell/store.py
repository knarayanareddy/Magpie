"""Sell-side state + receipts. Isolated from the buy loop (own files, own chain, own lock)."""
from __future__ import annotations
import contextlib, fcntl, json, os, time, uuid
from pathlib import Path

from .. import receipts as rc  # hash-chain writer/verifier (read-only reuse)

APP = Path(__file__).resolve().parents[2]


def sell_dir(out_dir: str | Path | None = None) -> Path:
    d = Path(out_dir) if out_dir else APP / "out" / "sell"
    (d / "photos").mkdir(parents=True, exist_ok=True)
    return d


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@contextlib.contextmanager
def locked(d: Path):
    """Serialize sell CLI invocations (phone quick-command + terminal may race)."""
    fh = open(d / ".lock", "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


class SellState:
    """{items: {item_id: {...}}, threads: {item_id: {...}}, seq: int}"""

    def __init__(self, d: Path):
        self.path = d / "state.json"
        self.data = {"items": {}, "threads": {}, "seq": 0}
        if self.path.exists():
            self.data.update(json.loads(self.path.read_text(encoding="utf-8")))

    def next_id(self, prefix: str) -> str:
        self.data["seq"] += 1
        return f"{prefix}{self.data['seq']:03d}"

    def item(self, item_id: str) -> dict:
        it = self.data["items"].get(item_id)
        if not it:
            raise KeyError(f"unknown item '{item_id}' (see: sell.py status)")
        return it

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)


def receipt(d: Path, item_id: str, action_state: str, reasons: list[str], *, actor: str = "agent",
            policy_branch: str, tier: str = "T1", scores: dict | None = None, extra: dict | None = None) -> dict:
    """Append one hash-chained receipt to out/sell/receipts.jsonl. Content-only (Art III)."""
    body = {"receipt_id": str(uuid.uuid4()), "ts": now(), "listing_id": item_id, "actor": actor,
            "hostile": "injection_or_jailbreak" in reasons or "offplatform_payment_request" in reasons,
            "policy_branch": policy_branch, "action_state": action_state, "tier": tier,
            "reason_codes": list(reasons), "scores": scores or {}, "side": "sell",
            "action_state_note": {"drafted": "drafted != posted/sent (Art VII.2)"}.get(action_state, "")}
    if extra:
        body.update(extra)
    body["input_hash"] = rc._row_hash({k: body[k] for k in ("listing_id", "policy_branch", "reason_codes", "scores")})
    rc.write(d / "receipts.jsonl", [body])
    return body
