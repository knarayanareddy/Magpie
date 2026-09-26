"""HEALTH — deterministic listing-content pre-filter from Apify metadata (no LLM).
Listings below HEALTH_FLOOR are auto-skipped before expensive vision/judge calls.
Art III & ORIGIN.md §4: Judged ONLY on listing content (photos, description, price, freshness).
ZERO seller profiling: no account age, no rating count, no person scoring.
Fail-closed: missing listing content scores 0 points."""
from __future__ import annotations
import datetime

HEALTH_FLOOR = 25  # below this -> auto-skip (reason: low_health)

# Listing-content weights (total = 100). ZERO seller-derived attributes (Art III).
W_DESC = 35         # description completeness & length
W_PHOTOS = 25       # photo availability (0 photos = 0, 1 = 15, 2+ = 25)
W_TITLE = 15        # descriptive title (>= 15 chars = 15, >= 5 chars = 9)
W_PRICE_VALID = 15  # valid asking price (only credited if listing has photo or substantive desc)
W_FRESHNESS = 10    # recently posted listing (< 168h)


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(0.0, min(1.0, (val - lo) / (hi - lo))) if hi > lo else 0.0


def score(item: dict, category_median: float | None = None) -> int:
    """Returns 0–100 health score based strictly on listing content.
    Zero seller attributes are scored (Article III / Anti-Profiling Rule)."""
    s = 0.0

    # 1. Title quality (15 pts)
    title = (item.get("title") or "").strip()
    if len(title) >= 15:
        s += W_TITLE
    elif len(title) >= 5:
        s += W_TITLE * 0.6

    # 2. Description completeness (35 pts)
    desc = (item.get("description") or "").strip()
    desc_len = len(desc)
    if desc_len >= 80:
        s += W_DESC
    elif desc_len >= 20:
        s += W_DESC * 0.65
    elif desc_len >= 5:
        s += W_DESC * 0.3

    # 3. Photos presence (25 pts)
    photos = len(item.get("images") or [])
    if photos >= 2:
        s += W_PHOTOS
    elif photos == 1:
        s += W_PHOTOS * 0.60
    # 0 photos = 0 pts

    # 4. Price validity & ratio vs comps (15 pts)
    # Price is only credited if listing has basic content (photo or description >= 10 chars)
    try:
        price = float(item.get("price_eur") or 0)
        if price > 0 and (photos > 0 or desc_len >= 10):
            if category_median and category_median > 0:
                ratio = price / category_median
                if 0.25 <= ratio <= 1.5:
                    s += W_PRICE_VALID
                elif 0.1 <= ratio < 0.25:
                    s += W_PRICE_VALID * 0.5  # suspicious low price
                else:
                    s += W_PRICE_VALID * 0.3
            else:
                s += W_PRICE_VALID  # price present and valid
    except (ValueError, TypeError):
        pass

    # 5. Freshness / Posting age (10 pts)
    posted = item.get("posted_at")
    if posted:
        try:
            dt = datetime.datetime.fromisoformat(posted.replace("Z", "+00:00"))
            hours = (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds() / 3600
            if hours < 48:
                s += W_FRESHNESS
            elif hours < 168:
                s += W_FRESHNESS * 0.6
            else:
                s += W_FRESHNESS * 0.2
        except Exception:
            s += W_FRESHNESS * 0.5  # valid string format present

    return int(round(s))
