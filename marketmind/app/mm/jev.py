"""JEV — Heuristic decision & safety triage rules (spec'd P2 for full model).
Provides fast, discriminative triage across closed sets without generative LLMs.
Art VI & Art IV.3: honest heuristic rules, no invented confidence numbers."""
from __future__ import annotations
import re

INJECTION_RE = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior|above|system)\s+(instructions|prompts|guidance|rules|directives)|"
    r"disregard\s+(all\s+)?(previous|prior|above|system)\s+(instructions|prompts|guidance|rules)|"
    r"jailbreak|accept\s+any\s+offer|forget\s+your\s+rules|override\s+policy|developer\s+mode)",
    re.I
)

DISPUTE_WORDS = (
    "broken", "kapot", "refund", "beschadigd", "defect", "return", "restitution",
    "terugbetaling", "doesnt work", "doesn't work", "werkt niet", "geld terug",
    "ik wil mijn geld", "oplichting", "politie"
)

AVAIL_WORDS = (
    "nog beschikbaar", "beschikbaar?", "still available", "available?", "is het nog",
    "kan ik het ophalen", "is dit er nog"
)


def classify_inbound(text: str) -> dict:
    """Classifies inbound buyer messages into closed-set action states.
    Returns: {label: str, outcome: str, tier: str, reply: str | None, reasons: list[str]}"""
    t = (text or "").lower()

    # 1. Hostile Screen / Prompt Injection (Art VI)
    if INJECTION_RE.search(t):
        return {
            "label": "injection_or_jailbreak",
            "outcome": "skipped",
            "tier": "T3",
            "reply": None,
            "reasons": ["injection_or_jailbreak"],
            "note": "hostile input — never auto, never engage (Art VI)",
        }

    # 2. Disputes — must ALWAYS escalate to human (Art VII.4 / T3)
    if any(m in t for m in DISPUTE_WORDS):
        return {
            "label": "dispute_t3",
            "outcome": "escalated",
            "tier": "T3",
            "reply": None,
            "reasons": ["dispute_t3"],
            "note": "human writes the reply — never auto (Art VII.4)",
        }

    # 3. Availability inquiries (T1 draft-assist)
    if any(m in t for m in AVAIL_WORDS):
        return {
            "label": "inbound_availability",
            "outcome": "drafted",
            "tier": "T1",
            "reply": "Hoi! Ja, is nog beschikbaar. Wanneer zou het jou uitkomen?",
            "reasons": ["inbound_availability"],
            "note": "draft availability response",
        }

    # 4. Unclassified inquiries escalate to human (T2)
    return {
        "label": "needs_human",
        "outcome": "escalated",
        "tier": "T2",
        "reply": None,
        "reasons": ["needs_human"],
        "note": "unclassified inquiry escalated to human",
    }


def classify_safety(text: str) -> dict:
    """Checks listing text against closed safety categories."""
    t = (text or "").lower()
    if INJECTION_RE.search(t):
        return {"top_label": "injection_or_jailbreak", "is_safe": False}
    if any(p in t for p in ("iban", "tikkie", "paypal.me", "wire transfer")):
        return {"top_label": "offplatform_payment", "is_safe": False}
    if any(c in t for c in ("replica", "namaak", "1:1 clone")):
        return {"top_label": "counterfeit", "is_safe": False}
    return {"top_label": "clean", "is_safe": True}
