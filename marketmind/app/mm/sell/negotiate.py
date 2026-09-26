"""NEGOTIATE — buyer-message co-pilot for OUR listings (US-9 AC-4). Every reply is a DRAFT; human approves.

Order of checks (fail-closed, Art VI): hostile/injection -> scam patterns (off-platform pay, courier/
"verification" links, overpay, shipping-only-abroad) -> dispute (T3 human) -> offer parse -> ladder.
Ladder (code, never a model): accept >= ask*ACCEPT_AT; counter halfway toward ask but never below floor;
at most MAX_COUNTER_ROUNDS counters per thread (killed list: unbounded auto-negotiation), then escalate.
Offers below floor*LOWBALL never get a counter below floor — they get the floor. The mandate ends at the
handshake: agreed price + pickup/shipping via the Marktplaats platform flow; no payment details, ever.
No buyer profiling (Art III): only the message text + classification are stored.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

from .. import config, jev

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skin"))
import policy as skin  # noqa: E402  (INJECTION_PHRASES / ADVANCE_FEE_RE — single source)

MAX_COUNTER_ROUNDS = config.MAX_COUNTER_ROUNDS          # 2 — shared with the buy side
ACCEPT_AT = 0.95                                          # offer >= 95% of ask => draft an accept
SCAM_RE = re.compile(
    r"(whatsapp|telegram\s*me|sms\s*me|bel\s*me\s*op\s*\+|\+?\d{2}[\s-]?\d{3}[\s-]?\d{3,}|"   # move off-platform
    r"verif(y|ieer|icatie)|bevestig\s*(je|uw)\s*(betaling|gegevens)|link\s*(sturen|gestuurd)|"   # phishing "verify" link
    r"(koerier|courier|dhl|ups|postnl)\s*(komt|haalt|regelt)|pakketdienst\s*van\s*mij|"         # buyer-arranged courier
    r"betaal\s*(te\s*)?veel|overpay|terugstorten|refund\s*the\s*difference|"                      # overpayment
    r"https?://|www\.|bit\.ly|\.link\b|\.xyz\b|"                                                   # any URL from a buyer
    r"verzend\s*naar\s*(het\s*)?buitenland|shipping\s*abroad|my\s*son\s*in)", re.I)
OFFER_RE = re.compile(r"(?:€\s*|eur(?:o)?\s*)?(\d{1,5}(?:[.,]\d{1,2})?)\s*(?:€|eur(?:o)?|,-)?", re.I)
OFFER_CUE_RE = re.compile(r"(\b(bied|bod|voor|geef|offer|would you take|kan het voor|eur|euro|piek)\b|€|\d\s*,-)", re.I)


def parse_offer(text: str, ask: int) -> float | None:
    """Deterministic euro amount. Ranking: explicit currency (€/euro/,-) > number right after an offer cue
    (bied/bod/geef/voor) > any number ≥ 10% of ask. Years, quantities and phone-ish numbers are ignored.
    Ambiguous (two different top-rank amounts) => None => human."""
    t = text or ""
    if not OFFER_CUE_RE.search(t):
        return None
    ranked: list[tuple[int, float]] = []
    for m in OFFER_RE.finditer(t):
        v = float(m.group(1).replace(",", "."))
        tok = m.group(0)
        explicit = bool(re.search(r"€|eur|,-", tok, re.I))
        before = t[max(0, m.start() - 14):m.start()].lower()
        after = t[m.end():m.end() + 8].lower()
        if not (1 <= v <= ask * 3) or (1990 <= v <= 2035 and not explicit):
            continue
        if re.match(r"\s*(stuks?|x\b|keer|gb|tb|jaar|maanden|cm|inch|mm)", after):
            continue                                            # quantity / spec, not money
        if explicit:
            ranked.append((0, v))
        elif re.search(r"(bied|bod|geef|voor|offer|take)\s*(je\s*|u\s*)?(max\s*)?$", before):
            ranked.append((1, v))
        elif v >= ask * 0.10:
            ranked.append((2, v))
    if not ranked:
        return None
    best = min(r for r, _ in ranked)
    top = {v for r, v in ranked if r == best}
    if best > 0 and len({v for _, v in ranked}) > 1:
        return None                     # "bied 150 of 170": no explicit currency + several amounts => human
    return top.pop() if len(top) == 1 else None


def classify(text: str) -> dict:
    """Closed set: injection | scam | dispute | availability | offer | question."""
    t = (text or "").strip()
    tl = t.lower()
    if jev.INJECTION_RE.search(tl) or any(p in tl for p in skin.INJECTION_PHRASES):
        return {"label": "injection_or_jailbreak", "tier": "T3"}
    if skin.ADVANCE_FEE_RE.search(t) or SCAM_RE.search(t):
        return {"label": "offplatform_payment_request", "tier": "T3"}
    j = jev.classify_inbound(t)
    if j["label"] == "dispute_t3":
        return {"label": "dispute_t3", "tier": "T3"}
    if OFFER_CUE_RE.search(tl) and OFFER_RE.search(tl):
        return {"label": "offer", "tier": "T2"}
    if j["label"] == "inbound_availability":
        return {"label": "availability", "tier": "T1"}
    return {"label": "question", "tier": "T2"}


def round5(x: float) -> int:
    return int(round(x / 5) * 5) if x >= 20 else int(round(x))


def decide(text: str, ask: int, floor: int, counters_used: int, last_counter: int | None = None) -> dict:
    """Returns {label, action: skip|escalate|draft, reasons, reply_nl|None, counter|None, accept|None}.
    Code decides; the reply is always a draft for one-tap human approval."""
    c = classify(text)
    base = {"label": c["label"], "tier": c["tier"], "reply_nl": None, "counter": None, "accept": None}
    if c["label"] == "injection_or_jailbreak":
        return {**base, "action": "skip", "reasons": ["injection_or_jailbreak"]}
    if c["label"] == "offplatform_payment_request":
        return {**base, "action": "skip", "reasons": ["offplatform_payment_request"],
                "note": "scam pattern (off-platform pay / link / courier / overpay) — never engage"}
    if c["label"] == "dispute_t3":
        return {**base, "action": "escalate", "reasons": ["dispute_t3"]}
    if c["label"] == "availability":
        return {**base, "action": "draft", "reasons": ["inbound_availability"],
                "reply_nl": "Hoi! Ja, is nog beschikbaar. Je kunt het ophalen of via Marktplaats laten verzenden — wat heeft je voorkeur?"}
    if c["label"] == "question":
        return {**base, "action": "escalate", "reasons": ["needs_human"],
                "note": "free-form question — the seller knows the item; Magpie does not invent answers"}
    offer = parse_offer(text, ask)
    if offer is None:
        return {**base, "action": "escalate", "reasons": ["offer_unparsed"]}
    if offer >= ask * ACCEPT_AT or (last_counter is not None and offer >= last_counter):
        return {**base, "action": "draft", "reasons": ["offer_accept"], "accept": round5(offer),
                "reply_nl": f"Hoi! €{round5(offer)} is akkoord. Zullen we het via Marktplaats afronden "
                            "(ophalen met Gelijk Oversteken, of verzenden met het Marktplaats-label)?"}
    if counters_used >= MAX_COUNTER_ROUNDS:
        # final position: accept only if >= floor, else human (never a 3rd counter)
        if offer >= floor:
            return {**base, "action": "escalate", "reasons": ["counter_cap_offer_above_floor"],
                    "note": f"€{offer:.0f} ≥ floor €{floor} after {counters_used} counters — accept? (human)"}
        return {**base, "action": "escalate", "reasons": ["counter_cap_reached"]}
    # counter: halfway between offer and (last counter or ask), never below floor, never above ask
    anchor = last_counter or ask
    counter = max(floor, min(ask, round5((offer + anchor) / 2)))
    if last_counter is not None and counter >= last_counter:
        counter = max(floor, round5(last_counter - max(5, (last_counter - floor) / 2)))
    if offer >= floor and counter <= offer:
        return {**base, "action": "draft", "reasons": ["offer_accept_above_floor"], "accept": round5(offer),
                "reply_nl": f"Hoi! €{round5(offer)} is prima. Zullen we het via Marktplaats afronden?"}
    final = counter == floor
    return {**base, "action": "draft", "reasons": ["counter_offer"] + (["counter_at_floor"] if final else []),
            "counter": counter,
            "reply_nl": (f"Hoi, bedankt voor je bod van €{offer:.0f}! " +
                         (f"€{counter} is echt mijn laagste prijs. " if final else f"Voor €{counter} is het van jou. ") +
                         "Ophalen of verzenden via Marktplaats kan allebei.")}
