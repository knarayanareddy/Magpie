"""Config — tier policy (plan.md §4), niche lock, budgets (fail closed on exceed, Art XII.3)."""
from __future__ import annotations
import os

NICHE = "games_consoles_camera"
MAX_COLD_OUTREACH = int(os.environ.get("MAX_COLD_OUTREACH", "5"))
OFFER_RATIO = 0.80          # H1 band: offers at <=80% of ask
OFFER_ROUND_TO = 5
OFFER_FLOOR_RATIO = 0.40    # never insult below 40% of ask -> escalate instead
MAX_COUNTER_ROUNDS = 2
DEAL_EUR_AUTO_CEILING = 200 # T3: deal > EUR200 never auto

CATEGORY_POLICY = {
    "games": "T2", "consoles": "T2", "camera": "T2", "other": "T2",
    "phones": "T3", "bikes": "T3", "ebikes": "T3",
}

ACTION_ALLOWLIST = {"send_message", "edit_own_price", "bump_own_listing"}  # Art XII.1 — nothing else exists

RESELLER = os.environ.get("NAMED_RESELLER", "unset")
MODE_NOTE = "simulated" if os.environ.get("MM_MODE", "sim") == "sim" else "live"


def tier_for(category: str) -> str:
    return CATEGORY_POLICY.get((category or "other").lower(), "T3")  # fail-closed: unknown categories not auto-eligible
