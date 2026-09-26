"""M1 state — seen-ids dedupe (T09), trust-tier memory + kill switch + caps (T11), priors (ledger)."""
from __future__ import annotations
import json, time
from pathlib import Path


class State:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data = {"seen": {}, "outreach_date": "", "outreach_count": 0, "paused": False,
                     "priors": {"H1": {"offers": 0, "accepted": 0}, "H2": {"morning": [], "evening": []}}}
        if self.path.exists():
            self.data.update(json.loads(self.path.read_text()))

    def is_seen(self, item_id: str) -> bool:
        return item_id in self.data["seen"]

    def mark_seen(self, item_id: str) -> None:
        self.data["seen"][item_id] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _roll_date(self) -> None:
        today = time.strftime("%Y-%m-%d", time.gmtime())
        if self.data["outreach_date"] != today:
            self.data["outreach_date"], self.data["outreach_count"] = today, 0

    def outreach_used(self) -> int:
        self._roll_date()
        return self.data["outreach_count"]

    def add_outreach(self) -> None:
        self._roll_date()
        self.data["outreach_count"] += 1

    def pause(self) -> None:
        self.data["paused"] = True
        self._kill_set = True

    def resume(self) -> None:
        self.data["paused"] = False
        self._kill_set = True

    def paused(self) -> bool:
        # Re-read the kill switch from disk: a phone /magpie_pause written mid-cycle by another
        # process must take effect on the very next item, not after the cycle (Art VII.3).
        if not getattr(self, "_kill_set", False) and self.path.exists():
            try:
                self.data["paused"] = bool(json.loads(self.path.read_text()).get("paused", self.data["paused"]))
            except Exception:
                pass
        return bool(self.data["paused"])

    def record_h1(self, accepted: bool, offer_id: str | None = None) -> None:
        self.data["priors"]["H1"]["offers"] += 1
        self.data["priors"]["H1"]["accepted"] += int(accepted)
        if "outcomes" not in self.data["priors"]["H1"]:
            self.data["priors"]["H1"]["outcomes"] = []
        if offer_id:
            self.data["priors"]["H1"]["outcomes"].append({
                "offer_id": offer_id,
                "accepted": bool(accepted),
                "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })

    def h1(self) -> dict:
        return self.data["priors"]["H1"]

    def add_seed(self, seed: dict) -> None:
        if "seed_buffer" not in self.data:
            self.data["seed_buffer"] = []
        self.data["seed_buffer"].append(seed)
        self.data["seed_buffer"] = self.data["seed_buffer"][-50:]

    def seed_buffer(self) -> list[dict]:
        return self.data.get("seed_buffer", [])

    def clear_seeds(self) -> None:
        self.data["seed_buffer"] = []

    @property
    def _data(self) -> dict:
        return self.data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not getattr(self, "_kill_set", False):
            self.paused()  # never clobber a kill switch another process set while we ran
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2))
        tmp.replace(self.path)  # atomic: a concurrent reader never sees a half-written file
