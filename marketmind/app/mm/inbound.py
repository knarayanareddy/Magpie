"""ListingPilot minimal (T12, M1) — inbound message triage. Disputes ALWAYS human (T3, Art VII.4).
Buyer messages are attacker-controlled: hostile-text screen first (Art VI)."""
from __future__ import annotations
from .decide import skin  # oracle phrases (INJECTION_PHRASES) — single source
from . import jev

DISPUTE_WORDS = (
    "broken", "kapot", "refund", "beschadigd", "defect", "return", "restitution",
    "terugbetaling", "doesnt work", "doesn't work", "werkt niet", "ik wil mijn geld",
    "geld terug", "oplichting"
)
AVAIL_WORDS = (
    "nog beschikbaar", "beschikbaar?", "still available", "available?", "is het nog",
    "kan ik het ophalen", "is dit er nog"
)


def classify(text: str, backend: str = "jev") -> dict:
    """Triage inbound buyer messages.
    Backend 'jev' uses discriminative pattern heuristics; 'legacy' uses exact oracle phrases."""
    if backend == "jev":
        return jev.classify_inbound(text)

    # Legacy baseline rule matcher
    t = (text or "").lower()
    if any(p in t for p in skin.INJECTION_PHRASES):
        return {"outcome": "skipped", "reasons": ["injection_or_jailbreak"], "tier": "T3", "reply": None,
                "note": "hostile input — never auto, never engage (Art VI)"}
    if any(w in t for w in DISPUTE_WORDS):
        return {"outcome": "escalated", "reasons": ["dispute_t3"], "tier": "T3", "reply": None,
                "note": "human writes the reply — never auto (Art VII.4)"}
    if any(w in t for w in AVAIL_WORDS):
        return {"outcome": "drafted", "reasons": ["inbound_availability"], "tier": "T1",
                "reply": "Hoi! Ja, is nog beschikbaar. Wanneer zou het jou uitkomen?"}
    return {"outcome": "escalated", "reasons": ["needs_human"], "tier": "T2", "reply": None}
