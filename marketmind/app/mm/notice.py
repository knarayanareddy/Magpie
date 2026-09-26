"""NOTICE — real-world data in (Apify in live mode, fixtures in sim). Never fetches seller-supplied URLs (Art XII.1)."""
from __future__ import annotations
import json, os, re, time, urllib.error, urllib.request
from pathlib import Path
from . import rerank

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
APIFY_BASE = "https://api.apify.com/v2"


class MMFeedError(RuntimeError):
    """Feed failure, cleanly reported (no URLs, no tokens in the message — audit C4)."""


def _safe_float(v) -> float:
    try:
        return float(str(v).replace("€", "").replace(",", "").strip() or 0)
    except (TypeError, ValueError):
        return 0.0  # audit R3: "€150" from an actor must not crash the run


def load(mode: str, measure: bool = False) -> tuple[list[dict], dict]:
    """Returns (listings, meta). meta carries honest timing notes (Art IV.3)."""
    t0 = time.perf_counter()
    if mode == "sim":
        listings = json.loads((FIXTURES / "apify_sample_dataset.json").read_text())
        comps_path = Path(os.environ.get("COMPS_PATH", FIXTURES / "comps_sample.json"))
        comps = json.loads(comps_path.read_text())
        meta = {"source": "fixtures", "mode": "sim",
                "timing_note": "simulated local read; live cycle time measured at T15/T05"}
    else:
        token = os.environ.get("APFY_TOKEN", "")
        actor = os.environ.get("APIFY_ACTOR_LISTINGS", "")
        if not token or not actor:
            missing = ", ".join(k for k in ("APFY_TOKEN", "APIFY_ACTOR_LISTINGS") if not os.environ.get(k))
            raise MMFeedError(f"{missing} missing — copy app/env.example to app/.env (WIRING §1)")
        tech_queries = [
            q.strip() for q in os.environ.get(
                "MP_TECH_QUERIES",
                "nintendo switch,ps5,iphone,macbook"
            ).split(",") if q.strip()
        ]
        max_per_query = max(5, int(os.environ.get("MP_MAX_PER_QUERY", "15")))
        # US-10 learned cadence: only queries whose learned interval has elapsed cost an Apify run.
        # Fail-open inside live.due_queries (any error => all queries, legacy behaviour).
        from .memory import live as mem
        due, cadence = mem.due_queries(tech_queries, mode)
        all_raw, fetched_q = [], []
        for q in due:
            body = json.dumps({
                "platform": "marktplaats.nl",
                "query": q,
                "maxListings": max_per_query
            }).encode()
            try:
                items = _apify_post(token, actor, body)
                for it in items:                      # attribute every item to the query that fetched it
                    if isinstance(it, dict) and not it.get("searchQuery"):
                        it["searchQuery"] = q
                all_raw.extend(items)
                fetched_q.append(q)
                mem.ingest(items, mode, queries_fetched=[q])
            except Exception:
                continue

        if not due:
            # nothing due by learned cadence: a quiet cycle, NOT a feed error (no alert, no Apify spend —
            # comps come from cache only: refreshing them with nothing to decide cost 246 s/$0.64 on Sat)
            comps = _load_comps_live(token, cache_only=True)
            meta = {"source": f"apify:{actor}", "mode": "live", "cadence": cadence, "queries_fetched": [],
                    "timing_note": "no query due (learned cadence) — 0 Apify listing runs"}
            meta["cycle_time_s"] = round(time.perf_counter() - t0, 3)
            return [], {**meta, "comps": comps}
        if not all_raw:
            raise MMFeedError("marktplaats_scraper_empty: no listings returned from targeted queries")

        listings = [_normalize(x) for x in all_raw]
        comps = _load_comps_live(token)
        meta = {"source": f"apify:{actor}", "mode": "live", "cadence": cadence, "queries_fetched": fetched_q}
    meta["cycle_time_s"] = round(time.perf_counter() - t0, 3)
    return listings, {**meta, "comps": comps}


def _apify_post(token: str, actor: str, body: bytes) -> list:
    """Token travels in the Authorization header, never in the URL (audit C4).
    Apify REST API expects username~actor-name in the URL path."""
    actor_id = actor.replace("/", "~")
    url = f"{APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items"
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.load(r)
    return out if isinstance(out, list) else out.get("items", [])


def _load_comps_live(token: str, cache_only: bool = False) -> dict:
    """cache_only=True (quiet cycle, nothing to decide): return the cache regardless of age, never scrape."""
    actor = os.environ.get("APIFY_ACTOR_COMPS", "")
    if not actor:
        return {}
    out_dir = Path(__file__).resolve().parent.parent / "out"
    cache_path = out_dir / "comps_cache.json"
    cache_ttl = int(os.environ.get("COMPS_CACHE_TTL_S", "7200"))
    force_refresh = os.environ.get("FORCE_COMPS_REFRESH", "0") == "1"

    if cache_only:
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
            return cached if isinstance(cached, dict) else {}
        except Exception:
            return {}
    if not force_refresh and cache_path.exists():
        try:
            mtime = cache_path.stat().st_mtime
            if (time.time() - mtime) < cache_ttl:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(cached, dict) and cached:
                    return cached
        except Exception:
            pass

    marketplace = os.environ.get("EBAY_MARKETPLACE", "DE")
    is_eur = marketplace in ("DE", "FR", "IT", "ES", "NL")
    fx_rate = 1.0 if is_eur else 0.92

    # European tech targets with minimum price floors to filter accessory noise
    queries = [
        ("nintendo switch", "nintendo switch konsole console", 50),
        ("ps5", "playstation 5 ps5 konsole console", 100),
        ("ps4", "playstation 4 ps4 konsole console", 40),
        ("macbook", "apple macbook pro air", 150),
        ("iphone", "apple iphone 13 14 15", 100),
        ("airpods", "apple airpods pro", 30),
        ("apple watch", "apple watch series", 50),
        ("canon", "canon eos kamera camera", 60),
    ]
    all_comps = {}
    basis = os.environ.get("COMPS_BASIS", "sold").lower()
    if basis == "sold":
        all_comps = _load_sold_comps(token, marketplace)
    for comp_key, query, min_price in queries:
        if comp_key in all_comps:
            continue  # sold comps found for this family; asking prices only as labelled fallback
        body = json.dumps({
            "searchQueries": [query],
            "marketplace": marketplace,
            "minPrice": min_price,
            "maxProductsPerSearch": 15
        }).encode()
        try:
            raw_items = _apify_post(token, actor, body)
        except Exception:
            continue
        filtered = rerank.filter_grounded_comps(comp_key, raw_items, min_confidence=0.70)
        source_items = filtered if filtered else raw_items
        prices = sorted(_safe_float(i.get("price")) * fx_rate for i in source_items
                        if i.get("price"))
        prices = [p for p in prices if p >= (min_price * 0.5)]
        if not prices:
            continue
        med = prices[len(prices) // 2]
        mad = sorted(abs(p - med) for p in prices)[len(prices) // 2] or 1.0
        all_comps[comp_key] = {
            "median": round(med, 2),
            "mad": round(mad, 2),
            "n": len(prices),
            "source": f"{actor} [{marketplace}]",
            "basis": "asking",
        }

    if all_comps:
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(all_comps, indent=2), encoding="utf-8")
        except Exception:
            pass

    return all_comps


# SOLD comps (completed sales, last 30 days, used condition) — the honest price basis for margin_z.
# Keywords are plain device names (eBay ANDs every word). Per-family exclusions drop successor models
# (Switch 2 is ~2.5x a Switch) and defect/parts sales; Art III: seller fields are never read.
SOLD_FAMILIES = [
    ("nintendo switch", "nintendo switch konsole", 50, r"switch\s*2|lite"),
    ("ps5", "playstation 5 konsole", 150, r"\bslim\b.*\bpro\b|\bportal\b"),
    ("ps4", "playstation 4 konsole", 40, r"\bps5\b|playstation\s*5"),
    ("macbook", "apple macbook air", 150, r"\bintel\b.*\b201[0-6]\b"),
    ("iphone", "iphone 14", 150, r"iphone\s*1[1235]\b|\bpro\s*max\b"),
    ("airpods", "apple airpods pro", 40, r"\bcase\s*only|\bnur\s*(case|ladecase)\b|einzeln|links|rechts"),
    ("apple watch", "apple watch series", 50, r"armband|band\s*only"),
    ("canon", "canon eos kamera", 80, r"objektiv\s*only|nur\s*objektiv"),
]
DEFECT_RE = re.compile(r"defekt|defect|bastler|bastel|ersatzteil|for parts|ohne funktion|kaputt|gesperrt|icloud", re.I)


def _load_sold_comps(token: str, marketplace: str) -> dict:
    actor = os.environ.get("APIFY_ACTOR_SOLD", "caffein.dev/ebay-sold-listings")
    site = {"DE": "ebay.de", "FR": "ebay.fr", "IT": "ebay.it", "ES": "ebay.es", "UK": "ebay.co.uk"}.get(marketplace, "ebay.de")
    count = int(os.environ.get("SOLD_COMPS_PER_FAMILY", "25"))
    out = {}
    for comp_key, keyword, min_price, exclude in SOLD_FAMILIES:
        body = json.dumps({"keywords": [keyword], "ebaySite": site, "daysToScrape": 30, "count": count,
                           "itemCondition": "used", "minPrice": min_price,
                           "includeCompletedListings": False}).encode()
        try:
            raw = _apify_post(token, actor, body)
        except Exception:
            continue
        ex = re.compile(exclude, re.I)
        cands = [{"title": i.get("title", ""), "price": _safe_float(i.get("soldPrice"))} for i in raw
                 if i.get("soldPrice") and (i.get("soldCurrency") in (None, "EUR"))
                 and not DEFECT_RE.search(i.get("title", "")) and not ex.search(i.get("title", ""))]
        grounded = rerank.filter_grounded_comps(comp_key, cands, min_confidence=0.70)
        prices = sorted(c["price"] for c in grounded if c["price"] >= min_price * 0.5)
        if len(prices) < 5:          # too thin to be a market price => leave to fallback / no_comps
            continue
        med = prices[len(prices) // 2]
        mad = sorted(abs(p - med) for p in prices)[len(prices) // 2] or 1.0
        out[comp_key] = {"median": round(med, 2), "mad": round(mad, 2), "n": len(prices),
                         "source": f"{actor} [{site}, sold 30d, used]", "basis": "sold"}
    return out


def _normalize(raw: dict) -> dict:
    """Map actor output -> canonical item (shape documented in WIRING.md §1)."""
    return {
        "id": raw.get("id") or raw.get("url", "")[-24:],
        "url": raw.get("url", ""),
        "title": raw.get("title", ""),
        "description": raw.get("description", ""),
        "price_eur": _safe_float(raw.get("price_eur") or raw.get("price")),
        "category": raw.get("category", "other"),
        "images": (raw.get("images") or [])[:3],
        "seller": raw.get("seller") or {},
        "posted_at": raw.get("posted_at") or "",
        "is_mine": bool(raw.get("is_mine", False)),
    }
