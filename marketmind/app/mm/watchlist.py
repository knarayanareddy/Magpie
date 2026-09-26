"""WATCHLIST — temporal revisit for uncertain listings (Darko improvement #5).
Listings escalated for recoverable reasons (e.g. no_comps) are cached for re-evaluation
on future cycles when comps or metadata become available. Expire after WATCHLIST_TTL_H.

Art VII.1: watchlist actions are logged with full traceability.
Policy gate is NOT modified — post-policy queue management only."""
from __future__ import annotations
import time

WATCHLIST_TTL_H = 72  # expire after 3 days
RECOVERABLE_REASONS = {"no_comps", "unknown"}
NON_RECOVERABLE_REASONS = {
    "injection_or_jailbreak", "weapon", "animal", "counterfeit",
    "pii", "other_illegal", "illegal_keyword", "offplatform_payment_request"
}


def should_watchlist(reason_codes: list[str]) -> bool:
    """Returns True if the escalation reason is recoverable and contains no hostile/illegal flags."""
    if any(rc in NON_RECOVERABLE_REASONS for rc in reason_codes):
        return False
    return any(rc in RECOVERABLE_REASONS for rc in reason_codes)


def add(state_data: dict, item: dict, reason_codes: list[str]) -> None:
    """Add a listing to the watchlist in state data."""
    wl = state_data.setdefault("watchlist", {})
    wl[item["id"]] = {
        "item": item,
        "reason_codes": list(reason_codes),
        "added_ts": time.time(),
        "revisit_count": 0,
    }


def get_pending(state_data: dict) -> list[dict]:
    """Returns watchlisted items that haven't expired, purging expired entries."""
    wl = state_data.get("watchlist", {})
    now = time.time()
    ttl_s = WATCHLIST_TTL_H * 3600
    pending = []
    expired_ids = []
    for lid, entry in list(wl.items()):
        age = now - entry.get("added_ts", 0)
        if age > ttl_s:
            expired_ids.append(lid)
        else:
            pending.append(entry)
    for lid in expired_ids:
        wl.pop(lid, None)
    return pending


def mark_revisited(state_data: dict, listing_id: str, resolved: bool) -> None:
    """Mark a watchlisted item as revisited. If resolved, removes it from watchlist."""
    wl = state_data.get("watchlist", {})
    if listing_id in wl:
        if resolved:
            del wl[listing_id]
        else:
            wl[listing_id]["revisit_count"] = wl[listing_id].get("revisit_count", 0) + 1
