"""RERANK — 2-Stage Grounded Comps Re-ranking (Jim Le Template 3 pattern).
Filters out accessories, bundles, cases, and spurious parts from scraped sold comps
before computing category median and MAD for margin_z."""
from __future__ import annotations
import re

ACCESSORY_KEYWORDS = (
    "case", "hoes", "hoesje", "cover", "bag", "tas", "etui",
    "cable", "kabel", "charger", "oplader", "adapter",
    "box only", "doos alleen", "leeg", "empty box",
    "screen protector", "schermfolie", "glass", "tempered glass",
    "grip", "dock only", "docking station only", "stand",
    "strap", "wrist strap", "polsband", "thumb grip",
    "replacement part", "onderdeel", "reparatie", "parts only", "for parts",
    "skin", "decal", "wrap", "sticker", "fan", "lüfter", "kühler", "radiator",
    "controller only", "alleen controller", "game only"
)


def score_comp_relevance(target_title: str, comp_title: str, target_price: float | None = None, comp_price: float | None = None) -> float:
    """Calculates semantic match confidence [0.0, 1.0] between target item and candidate comp."""
    tt = (target_title or "").lower()
    ct = (comp_title or "").lower()

    # If target is NOT explicitly an accessory, but comp is an accessory -> drop confidence
    target_is_acc = any(kw in tt for kw in ACCESSORY_KEYWORDS)
    comp_is_acc = any(re.search(rf"\b{re.escape(kw)}\b", ct) for kw in ACCESSORY_KEYWORDS)

    if comp_is_acc and not target_is_acc:
        return 0.20  # accessory noise for device target

    # Price ratio sanity check: if comp is < 30% of target price without target being cheap
    if target_price and comp_price and target_price > 50:
        ratio = comp_price / target_price
        if ratio < 0.25:
            return 0.35  # suspicious low price (likely accessory or broken)

    # Check keyword overlap of primary model tokens
    target_words = set(re.findall(r"\b[a-z0-9]{2,}\b", tt))
    comp_words = set(re.findall(r"\b[a-z0-9]{2,}\b", ct))

    if not target_words:
        return 0.50

    overlap = len(target_words & comp_words) / len(target_words)
    return round(min(1.0, 0.60 + 0.40 * overlap), 2)


def filter_grounded_comps(target_title: str, candidate_comps: list[dict], min_confidence: float = 0.85) -> list[dict]:
    """Drops noisy, off-target, or accessory comps with confidence < min_confidence."""
    grounded = []
    for c in candidate_comps:
        c_title = c.get("title", "")
        c_price = c.get("price_eur") or c.get("price")
        conf = score_comp_relevance(target_title, c_title, comp_price=c_price)
        if conf >= min_confidence:
            grounded.append({**c, "relevance_confidence": conf})
    return grounded


# Listing-side guard (buy side): a keyword hit like "iphone" in a REPAIR SERVICE or PART listing
# must not be grounded against device comps — that yields bogus margin_z (e.g. €55 back-glass repair
# vs €450 iPhone median => "pursue"). Word-boundary match; Dutch + English + German terms.
# Bundle words (oplader/hoesje/case/achterkant) deliberately excluded: 'MacBook met oplader' is a device;
# a lone cheap accessory still fails closed via margin_z > 2.5 => price_too_good.
NON_DEVICE_LISTING_RE = re.compile(
    r"\b(reparatie|reparaties|repareren|repair|reparatur|vervangen|vervanging|onderdel(en)?|onderdeel|"
    r"parts?|scherm\s*reparatie|accu\s*vervangen|batterij\s*vervangen|screenprotector|"
    r"gezocht|zoek(e|ende)?|inkoop|wij\s*kopen|opkoper|te\s*huur|huren|lessen|cursus|installeren|service)\b",
    re.I,
)


def is_non_device_listing(title: str) -> bool:
    """True when the listing title is a service, part, accessory or wanted-ad rather than the device."""
    return bool(NON_DEVICE_LISTING_RE.search(title or ""))
