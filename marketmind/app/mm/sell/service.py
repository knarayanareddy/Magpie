"""SERVICE — sell-side state machine (US-9). One function per human/agent step; every step receipts.

Item lifecycle:
  needs_confirmation -> confirmed -> priced | no_comps -> drafted -> posted -> (sold | withdrawn)
  privacy_review blocks drafting until the human clears it.
Message lifecycle (per item thread): received -> skip | escalate | draft -> approved (human) -> (human sends)
Code decides every transition; vision only proposes (Art V). Human steps carry actor=human.
"""
from __future__ import annotations
from pathlib import Path

from . import identify, intake, listing, negotiate, price as pricing
from .store import SellState, now, receipt


def run_intake(folder: Path, d: Path, *, vision=None) -> list[dict]:
    """Sanitize + group + vision proposal. Returns created items."""
    files = intake.collect(folder)
    if not files:
        raise ValueError(f"no photos ({', '.join(sorted(intake.EXTS))}) in {folder}")
    photos, unreadable = [], []
    for f in files:
        p = intake.sanitize(f, d / "photos")
        (photos.append(p) if p else unreadable.append(f.name))
    st = SellState(d)
    known = {ph["sha"] for it in st.data["items"].values() for ph in it["photo_meta"]}
    fresh = [p for p in photos if p["sha"] not in known]          # re-running intake is idempotent
    created = []
    for grp in intake.group(fresh):
        iid = st.next_id("s")
        prop = (vision or identify.propose)([d / "photos" / p["file"] for p in grp])
        privacy = prop["contains_face"] or prop["contains_document_or_address"]
        status = "privacy_review" if privacy else ("needs_confirmation")
        it = {"id": iid, "created": now(), "status": status, "photos": [p["file"] for p in grp],
              "photo_meta": [{k: p[k] for k in ("sha", "dhash", "w", "h")} for p in grp],
              "proposal": prop, "facts": None, "price": None, "draft": None, "posted": None}
        st.data["items"][iid] = it
        reasons = ["privacy_review"] if privacy else ["needs_confirmation"]
        if prop.get("multiple_items"):
            reasons.append("multiple_items_in_photo")
        if prop["vision"] != "ok":
            reasons.append(f"vision_{prop['vision']}")
        receipt(d, iid, "escalated", reasons, policy_branch="sell:intake", tier="T1",
                scores={"photos": len(grp), "model_certain_claimed": prop["model_certain"],
                        "vision": prop["vision"]})
        created.append(it)
    st.save()
    if unreadable:
        receipt(d, "intake", "skipped", ["unreadable_photos"], policy_branch="sell:intake",
                scores={"count": len(unreadable)})
    return created


def confirm(item_id: str, d: Path, *, model: str, brand: str | None = None, condition: str | None = None,
            defects: list[str] | None = None, accessories: list[str] | None = None,
            category: str | None = None, query: str | None = None, clear_privacy: bool = False,
            fetch=None) -> dict:
    """Human confirms identity (mandatory before pricing), then price is computed from sold comps."""
    st = SellState(d)
    it = st.item(item_id)
    if it["status"] in ("posted", "sold", "withdrawn"):
        raise ValueError(f"{item_id} is {it['status']} — confirm not allowed")
    if it["status"] == "privacy_review" and not clear_privacy:
        raise PermissionError(f"{item_id} flagged privacy_review (face/document in photo) — "
                              "remove those photos or re-run with --clear-privacy after checking")
    p = it["proposal"]
    model = " ".join((model or "").split())
    if len(model) < 2 or model.lower() == "unknown":
        raise ValueError("a concrete model is required (e.g. 'iPhone 14 128GB')")
    cond = condition or (p["condition"] if p["condition"] != "unknown" else "used")
    if cond not in identify.CONDITIONS:
        raise ValueError(f"condition must be one of {identify.CONDITIONS}")
    # Listing claims must be HUMAN-confirmed (US-9 AC-3): vision defect/accessory proposals are shown as hints,
    # never copied into the draft by default (measured: vision returned English 'cable, box' for a Dutch ad).
    it["facts"] = {"brand": brand or p["brand"], "model": model, "condition": cond,
                   "category": category if category in identify.CATEGORIES else p["category"],
                   "defects": list(defects or []), "accessories": list(accessories or []),
                   "vision_hints": {"defects": p["visible_defects"], "accessories": p["included_accessories"]},
                   "query": " ".join((query or model).split()), "confirmed_at": now()}
    receipt(d, item_id, "pursued_assisted", ["human_confirmed_identity"] + (["privacy_cleared"] if clear_privacy else []),
            actor="human", policy_branch="sell:confirm",
            scores={"vision_model_agreed": p["model"].lower() in model.lower() or model.lower() in p["model"].lower()})
    pr = pricing.price(it["facts"]["query"], cond, d, fetch=fetch)
    it["price"] = pr
    if pr["status"] == "ok":
        it["status"] = "priced"
        receipt(d, item_id, "priced", ["sold_comps"], policy_branch="sell:price",
                scores={k: pr[k] for k in ("ask", "floor", "median", "p40", "p60", "n", "condition_factor")},
                extra={"comps_source": pr["source"], "comps_basis": "sold"})
    else:
        it["status"] = "no_comps"
        receipt(d, item_id, "escalated", ["no_comps", pr.get("reason", "")], policy_branch="sell:price",
                scores={"n": pr.get("n", 0)})
    st.save()
    return it


def set_price(item_id: str, d: Path, *, ask: int, floor: int) -> dict:
    """Human override (also the path out of no_comps). Receipted actor=human."""
    if not (0 < floor <= ask):
        raise ValueError("need 0 < floor <= ask")
    st = SellState(d)
    it = st.item(item_id)
    if not it.get("facts"):
        raise PermissionError(f"{item_id}: confirm the item before pricing (identity first)")
    it["price"] = {**(it.get("price") or {}), "status": "ok", "ask": int(ask), "floor": int(floor), "basis": "human"}
    it["status"] = "priced"
    receipt(d, item_id, "pursued_assisted", ["human_price_override"], actor="human", policy_branch="sell:price",
            scores={"ask": ask, "floor": floor})
    st.save()
    return it


def draft(item_id: str, d: Path) -> dict:
    st = SellState(d)
    it = st.item(item_id)
    if it["status"] != "priced":
        raise PermissionError(f"{item_id} is {it['status']} — needs confirm + price first")
    it["draft"] = listing.render(it)
    it["status"] = "drafted"
    receipt(d, item_id, "drafted", ["listing_draft"], policy_branch="sell:listing",
            scores={"ask": it["price"]["ask"], "floor": it["price"]["floor"], "photos": len(it["photos"])})
    st.save()
    return it


def mark_posted(item_id: str, d: Path, *, url_or_ref: str = "") -> dict:
    st = SellState(d)
    it = st.item(item_id)
    if it["status"] != "drafted":
        raise PermissionError(f"{item_id} is {it['status']} — only a drafted listing can be marked posted")
    ref = url_or_ref.strip()
    if ref and not ref.startswith(("https://www.marktplaats.nl/", "m")):
        raise ValueError("ref must be a marktplaats.nl URL or an m-number")
    it["status"], it["posted"] = "posted", {"at": now(), "ref": ref[:200]}
    st.data["threads"].setdefault(item_id, {"counters": 0, "last_counter": None, "messages": []})
    receipt(d, item_id, "pursued_assisted", ["human_posted_listing"], actor="human", policy_branch="sell:post")
    st.save()
    return it


def message(item_id: str, d: Path, text: str) -> dict:
    """Buyer message in (pasted by the human). Code classifies + drafts; nothing is sent."""
    st = SellState(d)
    it = st.item(item_id)
    if it["status"] != "posted":
        raise PermissionError(f"{item_id} is {it['status']} — buyer messages only for posted listings")
    th = st.data["threads"].setdefault(item_id, {"counters": 0, "last_counter": None, "messages": []})
    dec = negotiate.decide(text, it["price"]["ask"], it["price"]["floor"], th["counters"], th["last_counter"])
    mid = st.next_id("msg")
    state = {"skip": "skipped", "escalate": "escalated", "draft": "drafted"}[dec["action"]]
    msg = {"id": mid, "at": now(), "text": text[:2000], "label": dec["label"], "action": dec["action"],
           "reasons": dec["reasons"], "reply_nl": dec["reply_nl"], "counter": dec["counter"],
           "accept": dec["accept"], "status": "awaiting_approval" if state == "drafted" else state,
           "note": dec.get("note", "")}
    th["messages"].append(msg)
    receipt(d, item_id, state, dec["reasons"], policy_branch=f"sell:negotiate:{dec['label']}", tier=dec["tier"],
            scores={"counter": dec["counter"], "accept": dec["accept"], "counters_used": th["counters"],
                    "floor": it["price"]["floor"], "ask": it["price"]["ask"]}, extra={"message_id": mid})
    st.save()
    return msg


def pending(d: Path) -> list[tuple[str, dict]]:
    st = SellState(d)
    out = [(iid, m) for iid, th in st.data["threads"].items() for m in th["messages"] if m["status"] == "awaiting_approval"]
    return sorted(out, key=lambda x: x[1]["at"])


def approve(d: Path, message_id: str | None = None) -> tuple[str, dict]:
    """Human one-tap approval of a drafted reply (oldest pending if no id). The human then sends it in the
    Marktplaats chat — Magpie has no messaging API (drafted != sent). Receipted pursued_assisted, actor=human."""
    st = SellState(d)
    if message_id is None:
        pend = pending(d)
        if not pend:
            raise KeyError("no pending draft to approve")
        message_id = pend[0][1]["id"]                  # oldest pending first
    for iid, th in st.data["threads"].items():
        for m in th["messages"]:
            if m["status"] != "awaiting_approval" or m["id"] != message_id:
                continue
            it = st.item(iid)
            if m["counter"] is not None:
                # re-check invariants at approval time (state may have moved since drafting)
                if m["counter"] < it["price"]["floor"] or th["counters"] >= negotiate.MAX_COUNTER_ROUNDS:
                    m["status"] = "escalated"
                    receipt(d, iid, "escalated", ["stale_counter_blocked"], policy_branch="sell:approve",
                            extra={"message_id": m["id"]})
                    st.save()
                    raise PermissionError(f"{m['id']}: counter no longer valid (floor/round cap) — escalated")
                th["counters"] += 1
                th["last_counter"] = m["counter"]
            m["status"], m["approved_at"] = "approved", now()
            if m["accept"] is not None:
                it["agreed_price"] = m["accept"]
            receipt(d, iid, "pursued_assisted", ["human_approved_reply"] + m["reasons"], actor="human",
                    policy_branch="sell:approve", scores={"counter": m["counter"], "accept": m["accept"],
                                                          "counters_used": th["counters"]},
                    extra={"message_id": m["id"], "action_state_note": "approved != sent: human sends in Marktplaats chat"})
            st.save()
            return iid, m
    raise KeyError(f"no pending draft {message_id} to approve")


def close(item_id: str, d: Path, *, outcome: str, price_eur: int | None = None) -> dict:
    if outcome not in ("sold", "withdrawn"):
        raise ValueError("outcome must be sold|withdrawn")
    st = SellState(d)
    it = st.item(item_id)
    it["status"], it["closed"] = outcome, {"at": now(), "price_eur": price_eur}
    receipt(d, item_id, "pursued_assisted", [f"human_marked_{outcome}"], actor="human", policy_branch="sell:close",
            scores={"price_eur": price_eur, "ask": (it.get("price") or {}).get("ask"),
                    "floor": (it.get("price") or {}).get("floor")})
    st.save()
    return it
