"""ACT — Browser-Use path (T13). Allowlist ONLY (Art XII.1): send_message | edit_own_price | bump_own_listing.
Fallback is always available: draft-assist (human presses Send). `drafted != sent` (Art VII.2)."""
from __future__ import annotations
import json, os, urllib.request
from urllib.parse import urlparse

from . import config

ALLOWLIST = config.ACTION_ALLOWLIST  # single source of truth (was a duplicate set — audit C9)
ALLOWED_HOSTS = {"www.marktplaats.nl", "marktplaats.nl", "www.ebay.nl", "www.ebay.com",
                 "www.ebay.be", "www.ebay.de", "www.ebay.fr", "www.ebay.co.uk",
                 "www.ebay.it", "www.ebay.es"}


def execute(action: str, target_url: str, payload: dict, receipt_id: str) -> dict:
    """Runs one allowlisted action in a recorded browser session. Anything else is a bug, not a feature."""
    if action not in ALLOWLIST:
        return {"status": "blocked", "reason": "not_in_allowlist", "action": action}   # fail closed
    if not _feed_url_ok(target_url):
        return {"status": "blocked", "reason": "url_not_from_feed", "note": "Art XII.1: never navigate seller-supplied URLs"}
    if not os.environ.get("BROWSER_USE_KEY"):
        return {"status": "draft-assist", "note": "no BROWSER_USE_KEY — human presses Send", "action": action}
    task = {"task": f"marketmind:{action}", "url": target_url, "payload": payload,
            "metadata": {"receipt_id": receipt_id, "allowlist": sorted(ALLOWLIST)},
            "record_session": True}
    req = urllib.request.Request("https://api.browser-use.com/v1/run-task",  # Browser-Use Cloud API
                                 data=json.dumps(task).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {os.environ['BROWSER_USE_KEY']}"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            out = json.load(r)
        return {"status": "pursued_assisted" if action == "send_message" else "pursued_auto",
                "session_id": out.get("id"), "action": action}
    except Exception as e:  # degrade, never fake
        return {"status": "draft-assist", "note": f"browser path failed: {type(e).__name__}", "action": action}


def _feed_url_ok(url: str) -> bool:
    """Strict host allowlist (audit C2: prefix check was spoofable via https://www.ebay.evil.com/...).
    https only, no userinfo, exact host match. Art XII.1: never navigate seller-supplied URLs."""
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower()
    except Exception:
        return False
    return p.scheme == "https" and host in ALLOWED_HOSTS and not p.username and not p.password
