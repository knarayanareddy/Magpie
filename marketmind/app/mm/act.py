"""ACT — draft-assist composer + allowlist + caps. `drafted` is not `sent` (Art VII.2). No money tools exist (Art V.3)."""
from __future__ import annotations
import datetime
from . import config


def round5(x: float) -> int:
    return int(max(config.OFFER_ROUND_TO, round(x / config.OFFER_ROUND_TO) * config.OFFER_ROUND_TO))


def _personalization_hook(item: dict, facts: dict, observe_data: dict | None = None) -> tuple[str, str]:
    """Selects grounded personalization hooks from structured facts (Darko improvement #6).
    Deterministic template selection — zero LLM hallucination risk (Art II.1)."""
    title = str(item.get("title", "item"))
    desc = str(item.get("description") or "").lower()
    posted = item.get("posted_at", "")

    # Hook 1: Verified condition from observe data
    if observe_data and observe_data.get("condition"):
        cond = str(observe_data["condition"]).lower()
        if cond in ("mint", "excellent", "as new", "zo goed als nieuw"):
            return (f"Je {title} ziet er uitstekend uit! ",
                    f"Your {title} looks in excellent condition! ")

    # Hook 2: Key accessories or box mentioned
    extras = ["doos", "box", "charger", "oplader", "controller", "hoes", "lens", "accu", "adapter"]
    found_extras = [kw for kw in extras if kw in desc]
    if found_extras:
        not_in_title = [kw for kw in found_extras if kw not in title.lower() and not (kw in ("box", "doos") and any(b in title.lower() for b in ("box", "doos")))]
        if not_in_title:
            return (f"Mooi dat je {title} met {not_in_title[0]} erbij aanbiedt! ",
                    f"Nice that you're offering {title} with {not_in_title[0]} included! ")
        return (f"Mooi dat je {title} zo compleet aanbiedt! ",
                f"Nice that you're offering {title} so complete! ")

    # Hook 3: Listing has been active for multiple days (>4 days)
    if posted:
        try:
            dt = datetime.datetime.fromisoformat(posted.replace("Z", "+00:00"))
            days = (datetime.datetime.now(datetime.timezone.utc) - dt).days
            if days >= 4:
                return (f"Ik zag dat je {title} al even te koop staat. ",
                        f"I noticed your {title} has been listed for a bit. ")
        except Exception:
            pass

    # Hook 4: Multiple photos provided
    photos = len(item.get("images") or [])
    if photos >= 4:
        return (f"Mooie foto's van je {title}! ",
                f"Great photos of your {title}! ")

    # Default hook
    return (f"Ik zag je {title} te koop staan. ",
            f"I saw your {title} listed. ")


def draft_offer(item: dict, facts: dict, used_tonight: int,
                observe_data: dict | None = None) -> dict | None:
    """Capped T2 offer (<=80% of ask, H1 band). None = over cap or floor breach -> caller escalates."""
    if used_tonight >= config.MAX_COLD_OUTREACH:
        return None
    ask = item["price_eur"]
    # Ensure offer strictly respects H1 ceiling (<= 80% of ask)
    offer = min(round5(ask * config.OFFER_RATIO), int(ask * config.OFFER_RATIO))
    if offer < ask * config.OFFER_FLOOR_RATIO or offer <= 0:
        return None
    sig = f" — {config.RESELLER}" if config.RESELLER and config.RESELLER != "unset" else ""

    hook_nl, hook_en = _personalization_hook(item, facts, observe_data)
    opt_out_nl = " (Laat gerust weten of dit past)"
    opt_out_en = " (No worries if not interested)"

    return {
        "offer_eur": offer,
        "offer_ratio": round(offer / ask, 2),
        "counter_round": 0,
        "max_counter_rounds": config.MAX_COUNTER_ROUNDS,
        "action": "send_message",              # allowlist (Art XII.1)
        "action_state": "drafted",             # human must press Send -> then `pursued_assisted`
        "text_nl": (f"Hoi! {hook_nl}"
                    f"Zou je €{offer} willen accepteren? Ik kan het ophalen wanneer het uitkomt.{opt_out_nl}{sig}"),
        "text_en": (f"Hi! {hook_en}"
                    f"Would you accept €{offer}? Happy to pick up whenever suits you.{opt_out_en}{sig}"),
    }


def reprice_own(item: dict) -> dict | None:
    """T1 own-account action (auto within tier): stale listing -> modest reprice. Allowlist: edit_own_price."""
    if not item.get("is_mine") or not item.get("stale_days"):
        return None
    new_price = round5(item["price_eur"] * 0.90)
    return {"action": "edit_own_price", "old_eur": item["price_eur"], "new_eur": new_price,
            "action_state": "pursued_auto", "reason": f"stale {item['stale_days']}d"}
