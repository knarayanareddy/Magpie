#!/usr/bin/env python3
"""US-11 actuator tests — every gate, offline (no browser, no network). Run: python3 marketmind/app/tests/test_actuator.py"""
from __future__ import annotations
import json, os, sys, tempfile, time
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from mm.actuator import gates  # noqa: E402
from mm.actuator.gates import Refused  # noqa: E402
from mm import receipts as rc  # noqa: E402

FAILS: list[str] = []


def check(cond, msg):
    print(("✓ " if cond else "✗ ") + msg)
    if not cond:
        FAILS.append(msg)


def refuses(fn, code):
    try:
        fn()
    except Refused as e:
        return e.code == code
    return False


AD = "https://www.marktplaats.nl/v/audio-tv-en-foto/koptelefoons/m2439594218-anker-soundcore-spaceone-koptelefoon"
BUY = "https://www.marktplaats.nl/v/spelcomputers-en-games/games-nintendo-switch/m2440117558-nintendo-switch-2"
td = Path(tempfile.mkdtemp())
d = gates.act_dir(td / "act")
state = td / "state.json"
state.write_text(json.dumps({"paused": False}))
ctx = {"own_listing_ids": {"m2439594218"}, "feed_urls": {AD, BUY}, "drafted_listing_urls": {BUY}, "state_path": state}

# 1. target allowlist (Art XII.1): only https www.marktplaats.nl /v/<cat>/<sub>/m<id>
check(gates.ad_id(AD) == "m2439594218", "real ad URL accepted → m-number")
for bad, code in [("http://www.marktplaats.nl/v/a/b/m2439594218", "target_not_allowlisted"),
                  ("https://evil.example/v/a/b/m2439594218", "target_not_allowlisted"),
                  ("https://www.marktplaats.nl.evil.com/v/a/b/m2439594218", "target_not_allowlisted"),
                  ("https://www.marktplaats.nl/v/a/b/m2439594218?redirect=https://evil", "target_not_allowlisted"),
                  ("https://user@www.marktplaats.nl/v/a/b/m2439594218", "target_not_allowlisted"),
                  ("https://www.marktplaats.nl/my-account/payments", "target_not_an_ad"),
                  ("https://link.marktplaats.nl/m2439594218", "target_not_allowlisted")]:
    check(refuses(lambda: gates.ad_id(bad), code), f"refused {code}: {bad[:60]}")

# 2. action allowlist — nothing but the three
for act in ("buy_now", "place_bid", "post_ad", "pay", "navigate", "click"):
    check(refuses(lambda: gates.request(act, AD, {}, context=ctx, d=d), "action_not_allowlisted"), f"action '{act}' refused")

# 3. provenance
check(refuses(lambda: gates.request("bump_own_listing", BUY, {}, context=ctx, d=d), "not_own_listing"),
      "bump on a stranger's ad refused (not in own registry)")
check(refuses(lambda: gates.request("send_message", AD, {"text": "Hoi"}, context=ctx, d=d), "no_draft_for_target"),
      "message to an ad without a Magpie draft refused")
check(refuses(lambda: gates.request("send_message", "https://www.marktplaats.nl/v/a/b/m1234567890-x", {"text": "Hoi"},
                                    context=ctx, d=d), "target_not_from_feed"), "message to a URL not from the feed refused")

# 4. params
check(refuses(lambda: gates.request("send_message", BUY, {"text": "Betaal via tikkie.me/xyz"}, context=ctx, d=d),
              "message_offplatform_content"), "outgoing message with payment link refused")
check(refuses(lambda: gates.request("send_message", BUY, {"text": "x" * 700}, context=ctx, d=d), "bad_message"), "overlong message refused")
check(refuses(lambda: gates.request("edit_own_price", AD, {"old_price_eur": 45, "new_price_eur": 60}, context=ctx, d=d),
              "price_change_out_of_bounds"), "price INCREASE refused (only downward reprices)")
check(refuses(lambda: gates.request("edit_own_price", AD, {"old_price_eur": 45, "new_price_eur": 10}, context=ctx, d=d),
              "price_change_out_of_bounds"), "reprice below 50% refused")

# 5. kill switch
state.write_text(json.dumps({"paused": True}))
check(refuses(lambda: gates.request("bump_own_listing", AD, {}, context=ctx, d=d), "kill_switch"), "kill switch blocks request")
state.write_text(json.dumps({"paused": False}))

# 6. happy path: request → approve (human) → claim (one-shot)
req = gates.request("edit_own_price", AD, {"old_price_eur": 45, "new_price_eur": 42}, context=ctx, d=d)
check(len(req["token"]) == 8 and "€45 → €42" in req["summary"], f"request mints token + summary ({req['summary']})")
check(refuses(lambda: gates.claim(req["token"], live=False, d=d, state_path=state), "not_human_approved"),
      "execute before human approval refused")
gates.approve(req["token"], d=d)
e = gates.claim(req["token"], live=False, d=d, state_path=state)
check(e["action"] == "edit_own_price" and e["params"]["new_price_eur"] == 42, "approved token claimed")
check(refuses(lambda: gates.claim(req["token"], live=False, d=d, state_path=state), "approval_token_already_used"),
      "token is one-shot (replay refused)")

# 7. kill switch between approval and execution
req2 = gates.request("bump_own_listing", AD, {}, context=ctx, d=d)
gates.approve(req2["token"], d=d)
state.write_text(json.dumps({"paused": True}))
check(refuses(lambda: gates.claim(req2["token"], live=True, d=d, state_path=state), "kill_switch"),
      "kill switch set AFTER approval still blocks execution")
state.write_text(json.dumps({"paused": False}))

# 8. expiry
req3 = gates.request("bump_own_listing", AD, {}, context=ctx, d=d)
gates.approve(req3["token"], d=d)
t = gates._load_tokens(d)
t[req3["token"]]["expires"] = time.time() - 1
gates._save_tokens(d, t)
check(refuses(lambda: gates.claim(req3["token"], live=True, d=d, state_path=state), "approval_token_invalid_or_expired"),
      "expired approval refused")

# 9. daily live budget
os.environ["ACT_MAX_PER_DAY"] = "1"
gates.receipt(d, "bump_own_listing", "m2439594218", "pursued_auto", ["renewed"], actor="agent", scores={"live": True})
req4 = gates.request("bump_own_listing", AD, {}, context=ctx, d=d)
gates.approve(req4["token"], d=d)
check(refuses(lambda: gates.claim(req4["token"], live=True, d=d, state_path=state), "act_budget_exhausted"),
      "daily live budget enforced")
os.environ.pop("ACT_MAX_PER_DAY")

# 10. receipts: chain intact, human approval recorded, refusals recorded, no credentials anywhere
ok, msg = rc.verify_chain(d / "receipts.jsonl")
rows = [json.loads(l) for l in (d / "receipts.jsonl").read_text().splitlines()]
check(ok, f"actuator receipt chain verifies ({msg})")
check(any(r["actor"] == "human" and "human_approved" in r["reason_codes"] for r in rows), "human approval is an actor=human receipt")
check(sum(r["action_state"] == "skipped" for r in rows) >= 10, "every refusal wrote a skipped receipt")
blob = (d / "receipts.jsonl").read_text() + (d / "approvals.json").read_text()
check(not any(w in blob.lower() for w in ("password", "wachtwoord", "cookie", "session_token")), "no credentials in receipts/approvals")

# 11. driver guards (pure regex parts)
from mm.actuator import driver  # noqa: E402
check(bool(driver.PAYMENT_RE.search("Kosten: € 2,99 — Betalen met iDEAL")), "payment guard trips on a paid-upsell dialog")
check(not driver.PAYMENT_RE.search("Verlengen is gratis"), "payment guard quiet on a free renew")
src = (APP / "mm" / "actuator" / "driver.py").read_text()
bump_src = src.split("def _bump_own_listing")[1].split("FLOWS =")[0]
locators = [ln for ln in bump_src.splitlines() if "get_by_role" in ln or "locator(" in ln]
check(locators and not any("omhoog" in ln.lower() for ln in locators),
      "bump flow never targets the paid 'Omhoogplaatsen' button (locators: Verlengen only)")
check(not any(s in src for s in ('name="Direct kopen"', "name='Direct kopen'", 'name="Bieden"')), "driver never locates Direct kopen / Bieden")

print("ACTUATOR TESTS:", "PASS" if not FAILS else f"FAIL ({len(FAILS)})")
sys.exit(1 if FAILS else 0)
