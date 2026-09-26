#!/usr/bin/env python3
"""Hero-run hardening tests: notifier debounce, pHash re-post guard, listing grounding, kill-switch race.
Offline except the optional live pHash probe (set PHASH_LIVE=1)."""
from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from mm import decide, notify, phash, rerank, state as state_mod  # noqa: E402

fails: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"{'✓' if cond else '✗'} {msg}")
    if not cond:
        fails.append(msg)


# 1. notifier: silence on routine cycles, debounce errors, drafts + kill-switch push
with tempfile.TemporaryDirectory() as td:
    dg = Path(td) / "digest.txt"
    dg.write_text("digest body")
    n = notify.Notifier(send=None)
    n.last_morning = notify._now().date()          # morning already sent today
    base = {"counts": {"skipped": 1, "escalated": 3, "drafted": 0, "pursued_auto": 0}, "paused": False}
    n.cycle(base, dg)
    check(n.sent == [], "routine escalate-only cycle sends nothing")
    n.cycle({**base, "error": "feed empty"}, dg)
    check(n.sent == [], "single transient feed error is debounced")
    n.cycle({**base, "error": "feed empty"}, dg)
    check(len(n.sent) == 1 and "failing 2 cycles" in n.sent[-1], "2nd consecutive error alerts once")
    n.cycle({**base, "error": "feed empty"}, dg)
    check(len(n.sent) == 1, "3rd error does not re-alert")
    n.cycle(base, dg)
    check("recovered" in n.sent[-1], "recovery line after error streak")
    n.cycle({**base, "counts": {**base["counts"], "drafted": 1}}, dg)
    check(n.sent[-1].startswith("📝") and "digest body" in n.sent[-1], "drafted cycle pushes digest")
    n.cycle({**base, "paused": True}, dg)
    check("kill-switch ON" in n.sent[-1], "kill-switch transition pushed")
    check(n.totals["escalated"] == 21, f"totals accumulate for morning summary ({n.totals['escalated']})")
    boom = notify.Notifier(send=lambda t: (_ for _ in ()).throw(RuntimeError("net down")))
    boom.armed("live", "v0", 300)
    check(True, "send failure does not raise into the loop")
    # US-10: memory savings accumulate and appear in the 08:00 summary
    mn = notify.Notifier(send=None)
    mn.last_morning = None
    mn._maybe_morning = lambda dp: None                         # hold the summary until we have totals
    for _ in range(3):
        mn.cycle({**base, "memory": {"cadence_skipped": 3, "cadence_fetched": 1, "comps_hits": 2, "verdict_hits": 1}}, dg)
    del mn._maybe_morning
    mn.last_morning = None
    import datetime as _dt
    _real_now = notify._now
    notify._now = lambda: _dt.datetime.now().replace(hour=8, minute=5)
    mn._maybe_morning(dg)
    notify._now = _real_now
    check(mn.sent and "9/12 listing fetches skipped" in mn.sent[-1] and "6 decisions on memory comps" in mn.sent[-1],
          f"morning summary reports memory savings ({(mn.sent or [''])[-1].splitlines()[1:2]})")

# 1b. own accounts: the reseller's own ads are recognised (by listing id or own-account id) and never become buy
#     candidates; a stranger's ad is untouched. Registry = out/own_accounts.json (gitignored).
with tempfile.TemporaryDirectory() as td:
    import json as _json, os as _os
    from mm import notice as _notice
    reg = Path(td) / "own.json"
    reg.write_text(_json.dumps({"seller_ids": ["111"], "listing_ids": ["m2445378351"]}))
    _os.environ["OWN_ACCOUNTS_FILE"] = str(reg)
    own_by_id = _notice._normalize({"listingId": "m2445378351", "sellerId": "999", "title": "MacBook Pro 16", "price": 2799})
    own_by_acct = _notice._normalize({"listingId": "m1", "sellerId": 111, "title": "Beixo vouwfiets", "price": 400})
    stranger = _notice._normalize({"listingId": "m2", "sellerId": "222", "title": "iPhone 14", "price": 300})
    del _os.environ["OWN_ACCOUNTS_FILE"]
    check(own_by_id["is_mine"] and own_by_acct["is_mine"] and not stranger["is_mine"],
          "own ads recognised by listing id AND own-account id; a stranger's ad is not")
    check("sellerId" not in own_by_acct and own_by_acct.get("seller") == {}, "canonical item carries no seller id (Art III)")

# 2. duplicate-photo signal (dHash): math, allowlist, redirects, near-dup detection, retry window
check(phash._allowed("https://evil.example.com/a.jpg") is None, "pHash refuses non-CDN host (Art XII.1)")
check(phash._allowed("http://images.marktplaats.com/a.jpg") is None, "pHash refuses plain http")
check(phash._allowed("//images.marktplaats.com/api/x.jpg") == "https://images.marktplaats.com/api/x.jpg",
      "pHash accepts protocol-relative CDN url")
check(phash.item_hash({"images": ["switch_a.jpg"]}) is None, "fixture (non-URL) image => None, fail-open")
idx: dict = {}
phash.remember("ffff0000ffff0000", idx, "a1")
check(phash.find_duplicate("ffff0000ffff0001", idx, "b2") == "a1", "hamming 1 => duplicate of prior id")
check(phash.find_duplicate("0000ffff0000ffff", idx, "b2") is None, "distant hash => not duplicate")
check(phash.find_duplicate("ffff0000ffff0000", idx, "a1") is None, "same listing id is not its own dup")
# redirect hop off the CDN allowlist is refused (Art XII.1)
import urllib.request as _u
_h = phash._AllowlistRedirects()
_req = _u.Request("https://images.marktplaats.com/a.jpg")
try:
    _h.redirect_request(_req, None, 302, "Found", {}, "https://evil.example.com/steal.jpg")
    check(False, "redirect to non-CDN host refused")
except Exception:
    check(True, "redirect to non-CDN host refused")
check(_h.redirect_request(_req, None, 302, "Found", {}, "https://images.marktplaats.com/b.jpg") is not None,
      "redirect within CDN allowed")
# failed hash retries after 2h, max 3 attempts (not never)
fl: dict = {}
check(phash.should_retry(fl, "z", now=1000.0), "never-tried listing is hashable")
phash.mark_failed(fl, "z", now=1000.0)
check(not phash.should_retry(fl, "z", now=1000.0 + 60), "no retry within 2h")
check(phash.should_retry(fl, "z", now=1000.0 + phash.RETRY_AFTER_S), "retry after 2h")
phash.mark_failed(fl, "z", now=9e4); phash.mark_failed(fl, "z", now=9e5)
check(not phash.should_retry(fl, "z", now=9e9), "gives up after 3 attempts")
if phash.backend():
    import io
    try:
        from PIL import Image
        im = Image.new("RGB", (64, 48))
        for x in range(64):
            for y in range(48):
                im.putpixel((x, y), (x * 4, y * 5, (x + y) * 2))
        b1 = io.BytesIO(); im.save(b1, "JPEG", quality=95)
        b2 = io.BytesIO(); im.resize((128, 96)).save(b2, "JPEG", quality=60)   # re-post: rescaled + recompressed
        h1, h2 = phash.dhash_bytes(b1.getvalue()), phash.dhash_bytes(b2.getvalue())
        check(h1 is not None and phash.hamming(h1, h2) <= phash.DUP_MAX_HAMMING,
              f"rescaled+recompressed copy stays within threshold (d={phash.hamming(h1, h2) if h1 and h2 else '?'})")
    except ImportError:
        pass
if os.environ.get("PHASH_LIVE") == "1":
    raw = json.loads(Path("/tmp/mp_raw.json").read_text())
    hs = [phash.item_hash({"images": r["images"]}) for r in raw[:6]]
    check(sum(h is not None for h in hs) >= 4, f"live CDN photos hash ({sum(h is not None for h in hs)}/6)")

# 3. grounding: service/part listings never grounded against device comps; honest reason codes
comps = {"iphone": {"median": 450.0, "mad": 50.0}, "nintendo switch": {"median": 190.0, "mad": 21.0}}
repair = {"id": "r", "title": "iPhone Achterkant Back glas vervangen Goedkoop Zwolle", "price_eur": 55.0, "description": ""}
f = decide.facts_for(repair, comps)
d = decide.decide(repair, f)
check(f["margin_z"] is None and d.action == "escalate" and d.reasons == ["not_device"],
      f"repair listing: no device comps, escalate not_device ({d.action} {d.reasons})")
bid = {"id": "b", "title": "iPhone 14 128GB Starlight", "price_eur": 0.0, "description": ""}
d = decide.decide(bid, decide.facts_for(bid, comps))
check(d.action == "escalate" and d.reasons == ["no_price"], f"'Bieden' €0 => escalate no_price ({d.reasons})")
ok = {"id": "o", "title": "Nintendo Switch V2 met Mario Kart", "price_eur": 150.0, "description": ""}
d = decide.decide(ok, decide.facts_for(ok, comps))
check(d.action == "pursue" and d.reasons == ["ok"], f"genuine device still pursues ({d.action} {d.reasons})")
unk = {"id": "u", "title": "Obscure tin toy", "price_eur": 20.0, "description": ""}
d = decide.decide(unk, decide.facts_for(unk, comps))
check(d.reasons == ["no_comps"], "unknown item keeps no_comps (watchlist-recoverable)")
check(not rerank.is_non_device_listing("MacBook Air M1 met oplader"), "bundle 'met oplader' stays a device")
for t_ in ("Nintendo Switch Lite Blauw met hoes", "Nintendo Switch 2 met Mario Kart World"):
    it_ = {"id": "l", "title": t_, "price_eur": 109.0, "description": ""}
    d_ = decide.decide(it_, decide.facts_for(it_, comps))
    check(d_.reasons == ["model_mismatch"], f"'{t_}' never priced vs full-Switch comps ({d_.reasons})")
acc = {"id": "c", "title": "SP Case voor iPhone 14 - Topstaat", "price_eur": 24.0, "description": ""}
d_ = decide.decide(acc, decide.facts_for(acc, comps))
check(d_.reasons == ["not_device"], f"'case voor iPhone' is an accessory, not a device ({d_.reasons})")
gen = {"id": "g", "title": "Iphone 11 128GB", "price_eur": 150.0, "description": ""}
d = decide.decide(gen, decide.facts_for(gen, comps))
check(d.action == "escalate" and d.reasons == ["model_mismatch"],
      f"iPhone 11 never priced vs iPhone 13-15 comps ({d.reasons})")

# 4. kill-switch race: phone pause written mid-cycle survives the loop's next save
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "state.json"
    loop = state_mod.State(p); loop.save()               # loop process holds state in memory
    phone = state_mod.State(p); phone.pause(); phone.save()  # /magpie_pause from Telegram
    check(loop.paused(), "loop sees phone pause on next item (re-read)")
    loop.mark_seen("x"); loop.save()
    check(json.loads(p.read_text())["paused"] is True, "loop save does not clobber phone pause")
    phone2 = state_mod.State(p); phone2.resume(); phone2.save()
    check(not loop.paused(), "loop sees phone resume")

print(f"\nHARDENING TESTS: {'PASS' if not fails else 'FAIL ' + str(fails)}")
sys.exit(1 if fails else 0)
