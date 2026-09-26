#!/usr/bin/env python3
"""Import the reseller's OWN Marktplaats ads into the sell co-pilot (US-9) + mark them as own in the buy loop.

Input: ad URLs / m-numbers (share links like https://link.marktplaats.nl/m2445378351?... are fine — only the
m-number is used; the URL itself is never fetched, Art XII.1). Data comes from the pinned Apify actor.

What it does
  1. Finds each ad through the listings actor (query variants from the title you supply or learned), reads the
     public ad fields. Seller ids are kept ONLY for the named human's own accounts (out/own_accounts.json) —
     that is self-identification, not profiling (Art III); no other seller's id is ever stored.
  2. Discovers the OTHER ads on those same accounts that appear in recent feeds / search results (the actor has
     no profile endpoint, so discovery is best-effort and labelled as such).
  3. Creates sell items in status `posted` (actor=human: the human posted them), with facts from the ad text,
     product key from the rules, and a price RECOMMENDATION from market memory / sold comps (never applied —
     repricing a live ad is a human action on Marktplaats; Magpie only drafts).
Usage:
  python3 tools/import_own_ads.py m2445378351 m2427939082 ...           # m-numbers or URLs
  python3 tools/import_own_ads.py --hint m2445378351="macbook pro 16 m4 pro" ...
"""
from __future__ import annotations
import argparse, concurrent.futures as cf, json, os, re, sys, time, urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
for l in (APP / ".env").read_text().splitlines():
    if "=" in l and not l.lstrip().startswith("#"):
        k, v = l.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))

from mm.memory import db as mdb, keys as mkeys, store as mstore  # noqa: E402
from mm.sell import identify, price as pricing  # noqa: E402
from mm.sell.store import SellState, locked, now, receipt, sell_dir  # noqa: E402

OWN = APP / "out" / "own_accounts.json"
M_RE = re.compile(r"\b(m\d{9,11})\b")
COND_MAP = {"new": "new", "like_new": "like_new", "used": "used", "good": "used", "fair": "used", "damaged": "damaged"}
CAT_HINTS = [(r"macbook|laptop|notebook", "laptop"), (r"iphone|smartphone|telefoon", "phone"), (r"ipad|tablet", "tablet"),
             (r"koptelefoon|headphone|hoofdtelefoon|oordop|airpods|soundcore|speaker", "audio"),
             (r"fiets|vouwfiets|bike|e-bike", "bike"), (r"switch|playstation|ps5|xbox|console", "console"),
             (r"camera|canon|nikon|sony a\d", "camera"), (r"horloge|watch", "watch")]


def m_number(s: str) -> str | None:
    m = M_RE.search(s or "")
    return m.group(1) if m else None


def apify_search(q: str, n: int = 60) -> list[dict]:
    body = json.dumps({"platform": "marktplaats.nl", "query": q, "maxListings": n, "scrapeDetails": True}).encode()
    actor = os.environ.get("APIFY_ACTOR_LISTINGS", "haketa/marktplaats-scraper").replace("/", "~")
    req = urllib.request.Request(f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items?timeout=240", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {os.environ['APFY_TOKEN']}"})
    try:
        with urllib.request.urlopen(req, timeout=280) as r:
            out = json.load(r)
        return out if isinstance(out, list) else []
    except Exception:
        return []


def query_variants(hint: str) -> list[str]:
    t = mkeys.norm(hint)
    words = [w for w in t.split() if len(w) > 2 and not w.isdigit()]
    vs = [t, " ".join(words[:3]), " ".join(words[:2]), words[0] if words else t]
    seen, out = set(), []
    for v in vs:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def find_ads(targets: dict[str, str]) -> dict[str, dict]:
    """targets: m-number -> title hint. Returns m-number -> raw actor item (with sellerId)."""
    found: dict[str, dict] = {}
    for round_ in range(4):
        todo = [(m, query_variants(h)[round_]) for m, h in targets.items()
                if m not in found and round_ < len(query_variants(h))]
        if not todo:
            break
        with cf.ThreadPoolExecutor(6) as ex:
            for (m, q), items in zip(todo, ex.map(lambda mq: apify_search(mq[1]), todo)):
                for it in items:
                    lid = str(it.get("listingId") or "")
                    if lid in targets and lid not in found:
                        found[lid] = it
    return found


def mp_asking(title: str, d: Path, own_sellers: set[str]) -> dict:
    """FALLBACK when eBay.de has no sold history (bikes, niche brands): what comparable Marktplaats ads ASK.
    Labelled basis=marktplaats_asking — an asking price is a ceiling signal, not a sale (ORIGIN claims rule).
    Comparable = title contains every model token of the query; own accounts and placeholder 'Bieden' prices
    excluded; ≥5 needed. Cached per query in out/sell/mp_asking_cache.json (6h)."""
    cache_p = d / "mp_asking_cache.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    for q in pricing.keyword_queries(title):
        hit = cache.get(q)
        if hit and time.time() - hit["at"] < 6 * 3600:
            rows = hit["rows"]
        else:
            rows = [{"title": str(i.get("title") or "")[:140], "price": mstore._f(i.get("price")),
                     "type": i.get("priceType"), "own": str(i.get("sellerId") or "") in own_sellers}
                    for i in apify_search(q, 60)]
            cache[q] = {"at": time.time(), "rows": rows}           # titles + prices only (no seller data kept)
            cache_p.write_text(json.dumps(cache, ensure_ascii=False))
        toks = q.split()
        comps = [r["price"] for r in rows if r["price"] and not r["own"]
                 and (r["type"] != "bidding" or r["price"] >= 20)
                 and all(t in mkeys.norm(r["title"]) for t in toks)]
        if len(comps) >= pricing.MIN_SALES:
            s = sorted(comps)
            med = pricing.quantile(s, 0.5)
            return {"status": "ok", "basis": "marktplaats_asking", "query": q, "n": len(s), "median": round(med, 2),
                    "p25": round(pricing.quantile(s, 0.25), 2), "p75": round(pricing.quantile(s, 0.75), 2),
                    "ask": pricing.round_price(pricing.quantile(s, 0.5)),
                    "floor": pricing.round_price(pricing.quantile(s, 0.25)),
                    "source": "marktplaats.nl current asking prices (NOT sold) via Apify listings actor"}
    return {"status": "no_comps", "reason": "no_sold_and_<5_comparable_asking"}


def recommend(title: str, key: str | None, cond: str, d: Path, own_sellers: set[str] | None = None) -> dict:
    """Sold-comps recommendation (memory first) — shown, never applied. Configurable items use a spec-precise
    keyword + facet filter; unkeyed items try brand+model keyword fallbacks (≤3 eBay runs); if eBay has no sold
    history, fall back to labelled Marktplaats ASKING prices."""
    if key:
        rec = pricing.price(pricing.spec_query(title) or key, cond, d, facet_title=title)
    else:
        rec = {"status": "no_comps", "reason": "no_keyword"}
        for q in pricing.keyword_queries(title):
            rec = pricing.price(q, cond, d, facet_title=title)
            if rec.get("status") == "ok":
                break
    if rec.get("status") != "ok":
        rec = mp_asking(title, d, own_sellers or set())
    return {k: rec.get(k) for k in ("status", "ask", "floor", "median", "n", "source", "reason", "cache_hit",
                                    "facets", "query", "basis", "p25", "p75")}


def refresh(d: Path) -> int:
    with locked(d):
        st = SellState(d)
        n = 0
        for iid, it in st.data["items"].items():
            if (it.get("facts") or {}).get("source") != "imported_own_ad":
                continue
            f = it["facts"]
            own = json.loads(OWN.read_text()) if OWN.exists() else {"seller_ids": []}
            it["recommendation"] = recommend(f["model"], f.get("product_key"), f["condition"], d, set(own["seller_ids"]))
            n += 1
            _print_row(iid, it)
        st.save()
    from mm.sell import board
    from mm.report import FOOTER
    board.write(d, SellState(d).data, FOOTER)
    print(f"refreshed {n} own-ad recommendation(s)")
    return 0


NL_MONTHS = {"jan": 1, "feb": 2, "mrt": 3, "apr": 4, "mei": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10,
             "nov": 11, "dec": 12}
STALE_DAYS = int(os.environ.get("OWN_STALE_DAYS", "14"))


def days_listed(nl_date: str | None) -> int | None:
    """'5 aug 26' -> days since (Marktplaats shows the listing/bump date in this form)."""
    m = re.match(r"\s*(\d{1,2})\s+([a-z]{3})\w*\s+(\d{2})", (nl_date or "").lower())
    if not m or m.group(2) not in NL_MONTHS:
        return None
    from datetime import date
    return (date.today() - date(2000 + int(m.group(3)), NL_MONTHS[m.group(2)], int(m.group(1)))).days


def _print_row(iid: str, it: dict) -> None:
    p, rec = it.get("posted") or {}, it.get("recommendation") or {}
    age = days_listed(p.get("listed_date"))
    stale = f" · ⏳ {age}d listed → bump/reprice candidate (T12)" if age is not None and age >= STALE_DAYS else \
        (f" · {age}d listed" if age is not None else "")
    listed = f"€{p['listed_price_eur']:.0f}" if p.get("listed_price_eur") else "Bieden (no price)"
    basis = "Marktplaats ASKING (not sold)" if rec.get("basis") == "marktplaats_asking" else "eBay.de sold"
    r = (f"{basis} median €{rec['median']} n={rec['n']} [{rec.get('query')}] → suggest ask €{rec['ask']} / floor €{rec['floor']}"
         if rec.get("status") == "ok" else f"no comps ({rec.get('reason') or rec.get('status')}) → you price it")
    print(f"  {iid} {p.get('ref')} [{it.get('account')}]{' (discovered)' if p.get('discovered') else ''} "
          f"{it['facts']['model'][:48]:48} listed {listed:17} · {r}{stale}")


def category_for(title: str) -> str:
    t = title.lower()
    return next((c for rx, c in CAT_HINTS if re.search(rx, t)), "other")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ads", nargs="*", help="ad URLs or m-numbers")
    ap.add_argument("--hint", action="append", default=[], help='m-number="title words" to find the ad in search')
    ap.add_argument("--discover", type=int, default=1, help="1 = also find other ads on the same accounts")
    ap.add_argument("--out", default=None)
    ap.add_argument("--refresh", action="store_true",
                    help="only recompute price recommendations for already-imported own ads (no ad search)")
    a = ap.parse_args()
    if a.refresh:
        return refresh(sell_dir(a.out))

    hints = {}
    for h in a.hint:
        m, _, words = h.partition("=")
        hints[m.strip()] = words.strip().strip('"')
    targets = {}
    for s in a.ads + list(hints):
        m = m_number(s)
        if m:
            targets[m] = hints.get(m, targets.get(m, ""))
    missing_hint = [m for m, h in targets.items() if not h]
    if missing_hint:
        print(f"❌ need a title hint to locate {missing_hint} in search: --hint {missing_hint[0]}=\"title words\"")
        return 2

    t0 = time.time()
    found = find_ads(targets)
    own = json.loads(OWN.read_text()) if OWN.exists() else {"seller_ids": [], "listing_ids": [], "accounts": {}}
    own.setdefault("urls", {})
    for m, it in found.items():
        if str(it.get("url", "")).startswith("https://www.marktplaats.nl/v/"):
            own["urls"][m] = it["url"]                   # public ad URL from the pinned feed (US-11 provenance)
        sid = str(it.get("sellerId") or "")
        if sid and sid not in own["seller_ids"]:
            own["seller_ids"].append(sid)
        own["accounts"].setdefault(sid, {"label": f"account {len(own['accounts']) + 1}", "added": now()})
        if m not in own["listing_ids"]:
            own["listing_ids"].append(m)

    # discovery: other ads by the same (own) accounts, from the searches we ran + the product-family feeds
    discovered: dict[str, dict] = {}
    if a.discover and own["seller_ids"]:
        qs = {q for h in targets.values() for q in query_variants(h)[:2]} | \
             {q.strip() for q in os.environ.get("MP_TECH_QUERIES", "").split(",") if q.strip()} | \
             {"fiets", "koptelefoon", "laptop", "vouwfiets", "apple"}
        with cf.ThreadPoolExecutor(6) as ex:
            for items in ex.map(lambda q: apify_search(q, 80), sorted(qs)):
                for it in items:
                    lid = str(it.get("listingId") or "")
                    if str(it.get("sellerId") or "") in own["seller_ids"] and lid not in targets and lid not in discovered:
                        discovered[lid] = it
        for lid, it in discovered.items():
            if lid not in own["listing_ids"]:
                own["listing_ids"].append(lid)
            if str(it.get("url", "")).startswith("https://www.marktplaats.nl/v/"):
                own["urls"][lid] = it["url"]
    OWN.parent.mkdir(parents=True, exist_ok=True)
    OWN.write_text(json.dumps(own, indent=2))

    d = sell_dir(a.out)
    created = []
    with locked(d):
        st = SellState(d)
        existing = {(it.get("posted") or {}).get("ref"): iid for iid, it in st.data["items"].items()}
        for lid, it in {**found, **discovered}.items():
            if lid in existing:
                continue
            title = str(it.get("title") or "")[:140]
            ask_now = mstore._f(it.get("price")) if it.get("price") else None
            key = mkeys.rules_key(title)
            cond = COND_MAP.get(str(it.get("condition") or ""), "used")
            iid = st.next_id("s")
            item = {"id": iid, "created": now(), "status": "posted", "photos": [], "photo_meta": [],
                    "proposal": {**identify.coerce({"model": title, "brand": "", "condition": cond}), "vision": "not_used",
                                 "contains_face": False, "contains_document_or_address": False},
                    "facts": {"brand": "", "model": title, "condition": cond, "category": category_for(title),
                              "defects": [], "accessories": [], "vision_hints": {"defects": [], "accessories": []},
                              "query": mkeys.norm(title), "product_key": key, "confirmed_at": now(),
                              "source": "imported_own_ad"},
                    "price": {"status": "ok", "ask": int(ask_now) if ask_now else 0, "floor": int(ask_now * 0.85) if ask_now else 0,
                              "basis": "own_listing_price" if ask_now else "bieden_no_price"},
                    "draft": None, "posted": {"at": now(), "ref": lid, "listed_price_eur": ask_now,
                                              "price_type": it.get("priceType"), "listed_date": it.get("date"),
                                              "discovered": lid in discovered},
                    "account": own["accounts"].get(str(it.get("sellerId") or ""), {}).get("label")}
            rec = item["recommendation"] = recommend(title, key, cond, d, set(own["seller_ids"]))
            st.data["items"][iid] = item
            st.data["threads"].setdefault(iid, {"counters": 0, "last_counter": None, "messages": []})
            receipt(d, iid, "pursued_assisted", ["human_posted_listing", "imported_own_ad"] +
                    (["discovered_on_own_account"] if lid in discovered else []), actor="human",
                    policy_branch="sell:import", scores={"listed_eur": ask_now, "rec_ask": rec.get("ask"),
                                                         "rec_median": rec.get("median"), "rec_n": rec.get("n")},
                    extra={"marktplaats_ref": lid})
            created.append((iid, lid, title, ask_now, item["posted"]["price_type"], rec, lid in discovered, item["account"]))
        st.save()
    from mm.sell import board
    from mm.report import FOOTER
    board.write(d, SellState(d).data, FOOTER)

    not_found = [m for m in targets if m not in found]
    print(f"own accounts recognised: {len(own['seller_ids'])} · own listings registered: {len(own['listing_ids'])} "
          f"· imported {len(created)} ({sum(c[6] for c in created)} discovered) · {time.time() - t0:.0f}s")
    final = SellState(d).data["items"]
    for iid, *_ in created:
        _print_row(iid, final[iid])
    if not_found:
        print(f"  ⚠ not found in search yet (new or low-ranked ads): {not_found} — retry with a better --hint")
    return 0


if __name__ == "__main__":
    sys.exit(main())
