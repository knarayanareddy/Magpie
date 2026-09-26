#!/usr/bin/env python3
"""US-10 market-memory tests — offline, temp DB. Run: python3 marketmind/app/tests/test_memory.py"""
from __future__ import annotations
import json, os, sqlite3, sys, tempfile, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
TMP = Path(tempfile.mkdtemp())
os.environ["MARKET_DB"] = str(TMP / "m.db")
from mm.memory import db, keys, store  # noqa: E402

fails: list[str] = []


def check(c, msg):
    print(f"{'✓' if c else '✗'} {msg}")
    if not c:
        fails.append(msg)


def iso(dt_):
    return dt_.strftime("%Y-%m-%dT%H:%M:%SZ")


NOW = datetime.now(timezone.utc)

# ---- 1. product keys: precision over recall, on real Marktplaats titles
cases = {
    "IPhone 14 Pro Max 256Gb": "iphone 14 pro max", "Iphone 14 pro 128GB - 80% batterij": "iphone 14 pro",
    "Iphone 14 Plus": "iphone 14 plus", "witte iphone 14": "iphone 14", "Iphone 14 128gb blauw z.g.a.n.": "iphone 14",
    "iPhone 15 Pro Max 256GB Zwart – Accu 100%": "iphone 15 pro max", "iPhone 13 mini 128GB": "iphone 13 mini",
    "Nintendo Switch Lite Blauw met hoes en oplader": "switch lite", "Nintendo Switch OLED Wit + 2 Mario Games – Compleet in doos": "switch oled",
    "Nintendo Switch V2 - Werkt goed, veel gebruikssporen": "switch", "Nintendo Switch 2 + 3 Games, 256GB SD kaart + Pro controller": "switch 2",
    "PS5 1TB Disc Edition + 2 controllers (incl Elden Ring & GT7)": "ps5 disc", "PS5 Slim Digital Edition": "ps5 digital",
    "Apple MacBook Pro 14\" M2 Pro (2023), 512GB SSD, Spacegrijs": "macbook pro m2 pro", "Nieuwe Macbook air m5 13 inch 16 gb 512ssd": "macbook air m5",
    "Macbook Pro 2019 | 16 inch | 16 GB RAM | 512 gb": "macbook pro intel 2019", "Apple AirPods Pro 2. Generation USB-C": "airpods pro 2",
    # must be None: accessories, repairs, games, controllers, wanted
    "SP Case voor iPhone 14 - Topstaat": None, "iPhone Achterkant Back glas vervangen Goedkoop Zwolle": None,
    "Diverse Nintendo Switch games": None, "Originele ps5 controllers || tmr sticks": None,
    "PS5 Reparaties | Stick drift | HDMI | GTA 6 klaar maken": None, "Limited Playstation Dualsense & Ps5 Pro Covers": None,
    "Gezocht: iPhone 14": None, "Logitech G29 Driving Force Racing Wheel + Shifter PS5/PS4/PC": None,
}
bad = [(t, keys.rules_key(t), e) for t, e in cases.items() if keys.rules_key(t) != e]
check(not bad, f"normalizer: {len(cases) - len(bad)}/{len(cases)} real titles keyed exactly (bad: {bad})")
check(keys.storage_gb("Iphone 14 128gb blauw") == 128 and keys.storage_gb("MacBook 1TB") == 1024, "storage facet parsed")

con = db.connect()
# ---- 2. ingest: seller fields dropped, first_seen/new counting, idempotent
raw = [{"listingId": "m1", "title": "Iphone 14 128GB zwart", "price": 250, "priceType": "fixed", "searchQuery": "iphone 14",
        "sellerName": "Jan Jansen", "sellerId": "u123", "location": "Delft", "description": "prima staat"},
       {"listingId": "m2", "title": "SP Case voor iPhone 14", "price": 10, "priceType": "fixed", "searchQuery": "iphone 14",
        "sellerName": "Piet"},
       {"listingId": "m3", "title": "Iphone 14 pro", "price": 1, "priceType": "bidding", "searchQuery": "iphone 14"}]
r1 = store.ingest_listings(con, raw, run_ref="run1", cost_usd=0.02, at=iso(NOW - timedelta(minutes=10)))
r2 = store.ingest_listings(con, raw, run_ref="run2", cost_usd=0.02, at=iso(NOW - timedelta(minutes=5)))
check(r1["new"] == 3 and r2["new"] == 0 and r2["fetched"] == 3, f"first fetch 3 new, repeat fetch 0 new ({r1['new']}, {r2['new']})")
dump = "\n".join(con.iterdump())
check(not any(s in dump for s in ("Jan Jansen", "u123", "Delft", "Piet", "seller")), "no seller name/id/location anywhere in the DB (Art III)")
check(con.execute("SELECT seen_count FROM listings WHERE listing_id='m1'").fetchone()[0] == 2, "seen_count increments on re-fetch")
check(con.execute("SELECT COUNT(*) FROM price_obs WHERE source='mp_ask'").fetchone()[0] == 1,
      "mp_ask obs only for keyed device + real price (case skipped, €1 'bieden' placeholder skipped)")
store.ingest_listings(con, raw, run_ref="run2", cost_usd=0.02, at=iso(NOW))
check(con.execute("SELECT COUNT(*) FROM fetches").fetchone()[0] == 2, "fetch rows idempotent per (run, query)")
check(store.mark_disappeared(con, "iphone 14", {"m1", "m2"}) == 1, "listing missing from a full fetch marked disappeared (time-on-market)")

# ---- 3. DB-first comps: basis isolation, freshness, min obs, outlier trim, grounding on ingest
sold = [{"title": f"Apple iPhone 14 128GB gebraucht {i}", "soldPrice": str(p), "soldCurrency": "EUR", "itemId": f"e{i}",
         "endedAt": (NOW - timedelta(days=1)).strftime("%Y-%m-%d")} for i, p in enumerate([220, 230, 235, 240, 250, 2400])]
sold.append({"title": "Apple iPhone 14 Pro 128GB", "soldPrice": "400", "soldCurrency": "EUR", "itemId": "epro",
             "endedAt": (NOW - timedelta(days=1)).strftime("%Y-%m-%d")})
n = store.ingest_ebay(con, sold, basis="ebay_sold", product_key="iphone 14")
check(n == 6, f"a 14 Pro sale is never filed under 'iphone 14' (grounded ingest, {n} rows)")
check(store.ingest_ebay(con, [{"title": "Apple iPhone 14 128GB Ersatzteil/Defekt", "soldPrice": "130", "soldCurrency": "EUR",
                                "itemId": "edef", "endedAt": NOW.strftime("%Y-%m-%d")}], basis="ebay_sold", product_key="iphone 14") == 0,
      "defect/parts sale never enters memory")
check(store.ingest_ebay(con, sold, basis="ebay_sold", product_key="iphone 14") == 0, "eBay ingest idempotent (UNIQUE source+ref)")
c = store.comps(con, "iphone 14", "ebay_sold")
check(c and c["n"] == 5 and c["median"] == 235 and c["source"] == "memory" and c["basis"] == "sold",
      f"memory comps: 3×-median outlier (€2400 lot) trimmed, n=5, median €235 ({c})")
check(store.comps(con, "iphone 14", "ebay_ask") is None, "sold obs never answer an asking-price request (no basis mixing)")
check(store.comps(con, "iphone 14 pro", "ebay_sold") is None, "1 obs < MIN_OBS => None => caller scrapes (fail-closed)")
check(store.comps(con, "iphone 14", "ebay_sold", max_age_h=1) is None, "stale obs (older than max age) never answer")
check(store.comps(con, None) is None, "no product key => no memory answer")
ms = [store.comps(con, "iphone 14", "ebay_sold")["lookup_ms"] for _ in range(50)]
check(sorted(ms)[25] < 5, f"memory comps p50 {sorted(ms)[25]:.3f} ms (< 5 ms)")

# ---- 4. verdict cache (T27): exact re-post reused, cheaper re-post re-decided
store.verdict_put(con, "Iphone 14 128GB zwart", "prima staat", "m1", "escalate", ["no_comps"], "v0", 250)
v = store.verdict_get(con, "iPhone 14 128gb ZWART!", "Prima staat.", 250)
check(v and v["action"] == "escalate" and v["cache_hit"] == "verdict", "re-post with same normalized text => prior verdict (0 tokens, 0 Apify)")
check(store.verdict_get(con, "Iphone 14 128GB zwart", "prima staat", 199) is None, "price DROP on re-post => fresh decision, never a stale verdict")
check(store.verdict_get(con, "Iphone 14 256GB zwart", "prima staat", 250) is None, "different text => miss")

# ---- 5. learned cadence: evidence-based, bounded, resets on activity
q = "macbook"
for d_ in range(5):                                   # 5 nights: 03h fetches never find anything
    for k in range(6):
        con.execute("INSERT INTO fetches(search_query, fetched_at, hour_local, n_fetched, n_new, cost_usd, run_ref) VALUES (?,?,?,?,?,?,?)",
                    (q, iso(NOW - timedelta(days=d_, minutes=k * 5)), 3, 10, 0, 0.015, f"n{d_}{k}"))
        con.execute("INSERT INTO fetches(search_query, fetched_at, hour_local, n_fetched, n_new, cost_usd, run_ref) VALUES (?,?,?,?,?,?,?)",
                    (q, iso(NOW - timedelta(days=d_, minutes=k * 5 + 1)), 19, 10, 2, 0.015, f"e{d_}{k}"))
con.commit()
night, evening = store.cadence(con, q, 3), store.cadence(con, q, 19)
check(night["interval_s"] == store.CADENCE_MAX_S, f"empty hour learned: 03h → {night['interval_s'] // 60} min ({night['why']})")
check(evening["interval_s"] == store.CADENCE_MIN_S, f"busy hour stays hot: 19h → {evening['interval_s'] // 60} min")
check(store.cadence(con, "brand-new-query", 3)["interval_s"] == store.CADENCE_MIN_S, "no evidence => default 5 min (never skips blindly)")
check(all(store.CADENCE_MIN_S <= store.cadence(con, q, h)["interval_s"] <= store.CADENCE_MAX_S for h in range(24)), "interval always within [5, 60] min")
con.execute("INSERT INTO fetches(search_query, fetched_at, hour_local, n_fetched, n_new, cost_usd, run_ref) VALUES (?,?,?,?,?,?,?)",
            (q, iso(NOW - timedelta(minutes=6)), 3, 10, 1, 0.015, "hot"))
con.commit()
# evaluate at 03h local (the hour learned as empty): the hot last fetch must override the 60-min cadence
three_am = datetime.now().replace(hour=3, minute=30, second=0).timestamp()
last_at = three_am - 360
con.execute("UPDATE fetches SET fetched_at=? WHERE run_ref='hot'", (iso(datetime.fromtimestamp(last_at, timezone.utc)),))
con.commit()
is_due, why = store.due(con, q, now_ts=three_am)
check(is_due and "hot" in why["why"], f"any new listing resets a cold hour to 5 min ({why['why']})")
con.execute("UPDATE fetches SET n_new=0 WHERE run_ref='hot'")
con.commit()
is_due, why = store.due(con, q, now_ts=three_am)
check(not is_due and why["interval_s"] == store.CADENCE_MAX_S, f"cold hour, 6 min since last empty fetch => not due ({why['why']})")

# ---- 6. feedback: correction memory surfaces for a near-identical photo, teaches the key cache
store.feedback(con, "model_id", "ffff0000ffff0000", proposed="Apple iPhone 13", corrected="iPhone 14 128GB", product_key="iphone 14")
h = store.correction_hint(con, "ffff0000ffff0001")
check(h and h["model"] == "iPhone 14 128GB", "near-identical photo => 'you labelled this iPhone 14 before' hint")
check(store.correction_hint(con, "0000ffff0000ffff") is None, "different photo => no hint")
k, how = keys.resolve(con, "Apple iPhone 13")
check(k == "iphone 14" and how == "cache:human", "human correction overrides the vision label in the key cache")

# ---- 7. JEV proposals are vetoed by deterministic guards (no network: stub the proposer)
_orig = keys.jev_propose
keys.jev_propose = lambda t, c, timeout_ms=4000: ("switch", 0.95)
k1, m1 = keys.resolve(con, "Switch spellen Mario Kart Zelda", use_jev=True)
k2, m2 = keys.resolve(con, "Nintendo Swich oled wit", use_jev=True)
keys.jev_propose = lambda t, c, timeout_ms=4000: ("iphone 14", 0.70)
k3, _ = keys.resolve(con, "Appel Iphone veertien", use_jev=True)
keys.jev_propose = _orig
check(k1 is None, "JEV 'switch' for a games-lot title vetoed by deterministic guard")
check(k2 == "switch" and m2 == "jev", "JEV proposal accepted when guards pass (typo title the rules can't key)")
check(k3 is None, "low-confidence JEV proposal (0.70 < 0.90) never becomes a key")
k4, m4 = keys.resolve(con, "Switch spellen Mario Kart Zelda", use_jev=True)
check(k4 is None and m4.startswith("cache:"), "second lookup answered from key cache (no JEV call)")

# ---- 8. telemetry + portability
lk = con.execute("SELECT kind, SUM(hit), COUNT(*) FROM lookups GROUP BY kind").fetchall()
check({r[0] for r in lk} >= {"comps", "verdict"}, f"every memory read is measured in `lookups` ({[tuple(r) for r in lk]})")
schema = "\n".join(r[0] for r in con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"))
check("TRIGGER" not in schema.upper() and "REFERENCES" not in schema.upper(), "schema portable: no triggers / FK cascades")
check(con.execute("PRAGMA journal_mode").fetchone()[0] == "wal", "WAL mode (concurrent readers while the loop writes)")
ro = db.connect(readonly=True)
try:
    ro.execute("INSERT INTO meta VALUES ('x','y')")
    check(False, "read-only connection rejects writes")
except sqlite3.OperationalError:
    check(True, "read-only connection rejects writes")

print(f"\nMEMORY TESTS: {'PASS' if not fails else 'FAIL ' + str(fails)}")
sys.exit(1 if fails else 0)
