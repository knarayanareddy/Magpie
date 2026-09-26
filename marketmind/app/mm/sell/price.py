"""PRICE — ask + floor COMPUTED from eBay.de SOLD comps for a human-confirmed query (US-9 AC-2).

Never asked of a model (Art V.1). Fail-closed: < MIN_SALES grounded sales => no_comps => human prices it.
Reuses notice._apify_post / rerank / notice.DEFECT_RE read-only; own cache out/sell/comps_cache.json so the
buy loop's comps cache is never touched.
"""
from __future__ import annotations
import json, os, re, time
from pathlib import Path

from .. import notice, rerank

MIN_SALES = 5
CACHE_TTL_S = int(os.environ.get("SELL_COMPS_TTL_S", "21600"))   # 6h: sold prices move slowly
ASK_Q = float(os.environ.get("SELL_ASK_QUANTILE", "0.60"))
FLOOR_Q = float(os.environ.get("SELL_FLOOR_QUANTILE", "0.40"))
CONDITION_FACTOR = {"new": 1.10, "like_new": 1.00, "used": 0.95, "damaged": 0.60, "unknown": 0.90}
EXCLUDE_ALWAYS = re.compile(r"\b(defekt|defect|bastler|ersatzteil|for parts|kaputt|gesperrt|icloud|nur\s*(ovp|karton|box)|leerkarton)\b", re.I)

# CONFIG FACETS (bug found Sat on the user's own MacBook Pro 16" M4 Pro 48GB: the product key "macbook pro m4 pro"
# pooled 14"/16GB base machines and priced a €3,000 laptop at €1,700). When the query states a facet, a comp must
# state the SAME value; a comp that doesn't state it is dropped for high-value configurable items (fail-closed).
_SCREEN_RE = re.compile(r"\b(1[1-7])(?:[.,]\d)?\s*(?:\"|”|″|''|-?\s*inch|-?\s*zoll|-?\s*in\b|-?\s*inches)", re.I)
_RAM_VALUES = {8, 12, 16, 18, 24, 32, 36, 48, 64, 96, 128}
_GB_RE = re.compile(r"\b(\d{1,4})\s*(gb|tb)\b", re.I)


def facets(title: str) -> dict:
    t = title or ""
    out: dict = {}
    m = _SCREEN_RE.search(t)
    if m:
        out["screen"] = int(m.group(1))
    # RAM only exists as a facet for computers; a phone's "128GB" is storage
    computer = bool(re.search(r"\b(macbook|laptop|notebook|imac|mac\s*mini|mac\s*studio|surface|thinkpad|ram)\b", t, re.I))
    ram, storage = None, None
    for n, unit in ((int(a), u.lower()) for a, u in _GB_RE.findall(t)):
        gb = n * 1024 if unit == "tb" else n
        if computer and unit == "gb" and n in _RAM_VALUES and ram is None and gb < 256:
            ram = gb
        elif gb >= 64 and storage is None:
            storage = gb
    if ram:
        out["ram"] = ram
    if storage:
        out["storage"] = storage
    return out


def facet_filter(query: str, comps: list[dict], strict: bool) -> tuple[list[dict], dict]:
    """Keep comps whose facets match every facet the query states. strict=True also drops comps that don't
    state a facet the query states (used for laptops/tablets where config dominates price)."""
    want = facets(query)
    if not want:
        return comps, want
    kept = []
    for c in comps:
        have = facets(c.get("title", ""))
        ok = True
        for k, v in want.items():
            if k in have:
                ok = ok and have[k] == v
            elif strict:
                ok = False
        if ok:
            kept.append(c)
    return kept, want


def strict_facets_for(query: str) -> bool:
    return bool(re.search(r"\b(macbook|laptop|notebook|ipad|imac|mac\s*mini|mac\s*studio|surface)\b", query or "", re.I))


_VARIANTS = r"(pro|max|ultra|plus|lite|mini|se|oled|slim)"


def _model_tail(title: str, anchor: str) -> str | None:
    """The variant word directly after the model anchor ('space one PRO' -> 'pro'), or '' for the base model."""
    m = re.search(re.escape(anchor) + r"\s*[-\s]?\s*" + _VARIANTS + r"\b", title, re.I)
    return m.group(1).lower() if m else ""


def variant_filter(query_title: str, comps: list[dict]) -> list[dict]:
    """Base model vs variant (Space One vs Space One Pro, Switch vs Switch Lite): the word right after the
    model name must agree. Anchor = the longest run of query words (≥2) found in a comp title. Only applies
    when the query's own title makes the variant unambiguous; otherwise comps are returned unchanged."""
    norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower())
    comp_text = " ".join(norm(c["title"]) for c in comps)
    words = []
    for w in re.findall(r"[a-z0-9]+", (query_title or "").lower()):
        # split a joined model word ("spaceone") when the comps spell it apart ("space one")
        split = next((f"{w[:i]} {w[i:]}" for i in range(3, len(w) - 2) if f"{w[:i]} {w[i:]}" in comp_text), None)
        words.extend(split.split() if split else [w])
    words = [w for w in words if len(w) > 1]
    query_title = " ".join(words)
    anchor = None
    for n in range(min(4, len(words)), 1, -1):
        for i in range(len(words) - n + 1):
            cand = " ".join(words[i:i + n])
            if re.search(_VARIANTS + r"$", cand):
                continue
            hits = sum(1 for c in comps if cand in re.sub(r"[^a-z0-9]+", " ", c["title"].lower()))
            if hits >= max(3, len(comps) // 3):
                anchor = cand
                break
        if anchor:
            break
    if not anchor:
        return comps
    want = _model_tail(norm(query_title), anchor)
    return [c for c in comps if anchor not in norm(c["title"]) or _model_tail(norm(c["title"]), anchor) == want]


def quantile(xs: list[float], q: float) -> float:
    """Linear-interpolated quantile of a non-empty sorted list (deterministic, no numpy)."""
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def round_price(x: float) -> int:
    """Marktplaats-style round numbers: <50 -> €1, <200 -> €5, else €10."""
    step = 1 if x < 50 else 5 if x < 200 else 10
    return int(max(step, round(x / step) * step))


def _fetch_sold(query: str, min_price: int) -> list[dict]:
    token = os.environ.get("APFY_TOKEN", "")
    if not token:
        raise RuntimeError("APFY_TOKEN missing")
    actor = os.environ.get("APIFY_ACTOR_SOLD", "caffein.dev/ebay-sold-listings")
    body = json.dumps({"keywords": [query], "ebaySite": "ebay.de", "daysToScrape": 30,
                       "count": int(os.environ.get("SELL_COMPS_COUNT", "30")), "itemCondition": "used",
                       "minPrice": min_price, "includeCompletedListings": False}).encode()
    return notice._apify_post(token, actor, body)


def _memory_prices(q: str, facet_title: str | None = None, strict: bool = False) -> tuple[list[float], dict] | None:
    """US-10 DB-first: fresh eBay-sold observations for the query's product key from out/market.db, with the
    same config-facet filter as the scraped path. None (=> scrape) when disabled, unkeyable, or < MIN_SALES."""
    if os.environ.get("SELL_MEMORY", "1") != "1":
        return None
    try:
        from ..memory import db as mdb, keys as mkeys, store as mstore
        key = mkeys.rules_key(q)
        if not key:
            return None
        con = mdb.connect()
        t0 = time.perf_counter()
        rows = [{"title": t, "price": p} for p, t in mstore.fresh_obs(con, key, "ebay_sold")
                if not EXCLUDE_ALWAYS.search(t) and not notice.DEFECT_RE.search(t)]
        rows, _ = facet_filter(facet_title or q, rows, strict)
        tier = re.search(r"\bm\d\s*(pro|max|ultra)\b", facet_title or q, re.I)
        if tier:
            rows = [r for r in rows if (m := re.search(r"\bm\d\s*(pro|max|ultra)\b", r["title"], re.I)) is None
                    or m.group(1).lower() == tier.group(1).lower()]
        obs = [r["price"] for r in rows]
        hit = len(obs) >= MIN_SALES
        ms = mstore._lookup(con, "comps", hit, t0, f"sell|{key}|n={len(obs)}")
        con.commit()
        con.close()
        return (obs, {"product_key": key, "lookup_ms": round(ms, 3)}) if hit else None
    except Exception:
        return None                                   # memory is an accelerator, never a single point of failure


def _memory_writeback(q: str, raw: list[dict]) -> None:
    if os.environ.get("SELL_MEMORY", "1") != "1":
        return
    try:
        from ..memory import db as mdb, keys as mkeys, store as mstore
        con = mdb.connect()
        mstore.ingest_ebay(con, raw, basis="ebay_sold", product_key=mkeys.rules_key(q))
        con.close()
    except Exception:
        pass


_FILLER = re.compile(r"\b(met|en|in|zeer|goed|goede|staat|zgan|z\.g\.a\.n|nieuw|nieuwe|als|te|koop|de|het|een|voor|"
                     r"unisex|incl|inclusief|origineel|originele|perfecte|mooie|nette|gebruikt|versnellingen|"
                     r"koptelefoon|hoofdtelefoon|vouwfiets|fiets|laptop|telefoon|anc|draadloos|draadloze|\d+\s*gb|"
                     r"aandrijfmechanism\w*|share)\b", re.I)


_JOINED = {"spaceone": "space one", "airpods": "airpods", "powerbeats": "powerbeats", "soundlink": "soundlink",
           "quietcomfort": "quietcomfort", "playstation": "playstation"}
_BRANDS = {"anker", "soundcore", "apple", "samsung", "sony", "bose", "jbl", "philips", "dahon", "brompton", "beixo",
           "gazelle", "batavus", "cortina", "sparta", "nintendo", "microsoft", "lenovo", "dell", "hp", "asus", "garmin"}


def keyword_queries(title: str) -> list[str]:
    """eBay keyword fallbacks for an unkeyed item: brand + model tokens, most specific first. A query must keep at
    least one MODEL token (non-brand word) — "anker soundcore" alone matched every Anker product (earbuds,
    speakers) and priced a Space One headphone at €37. Joined model words are split ("spaceone" -> "space one").
    'Dahon MU D8 Vouwfiets met 8 versnellingen in zeer goed staat' -> ['dahon mu d8', 'dahon mu']."""
    t = _FILLER.sub(" ", title.lower())
    for joined, split in _JOINED.items():
        t = re.sub(rf"\b{joined}\b", split, t)
    words = [w for w in re.findall(r"[a-z0-9]+", t) if len(w) > 1]            # bare digits ("8 versnellingen") are noise
    out = []
    for n in (4, 3, 2):
        if len(words) >= n:
            cand = words[:n]
            # drop a leading brand if the next brand already names the line ("anker soundcore space one" -> keep both,
            # but the query must still contain a model token)
            if not any(w not in _BRANDS for w in cand):
                continue
            q = " ".join(cand)
            if q not in out:
                out.append(q)
        # sub-brand form: "soundcore space one" (without the parent brand) is how eBay titles usually read
        if n == 4 and len(words) >= 3 and words[0] in _BRANDS and words[1] in _BRANDS:
            q = " ".join(words[1:4])
            if q not in out:
                out.append(q)
    return out[:3] or [title.lower()[:40]]


def spec_query(title: str) -> str | None:
    """Precise eBay keyword for a configurable item: product key + stated facets ("macbook pro m4 pro 16 48gb")."""
    from ..memory import keys as mkeys
    key = mkeys.rules_key(title)
    if not key:
        return None
    f = facets(title)
    parts = [key] + ([str(f["screen"])] if "screen" in f else []) + ([f"{f['ram']}gb"] if "ram" in f else [])
    return " ".join(parts)


def price(query: str, condition: str, sell_dir: Path, fetch=None, min_price: int = 5, facet_title: str | None = None) -> dict:
    """Returns {status: ok|no_comps|error, ask, floor, median, p40, p60, n, basis, source, query, samples}.
    Lookup order (US-10): market memory (≥5 fresh sold obs for the product key) -> local 6h cache -> Apify."""
    q = " ".join((query or "").lower().split())[:80]
    if len(q) < 3:
        return {"status": "no_comps", "reason": "empty_query", "query": q}
    ftitle = facet_title or q
    strict = strict_facets_for(ftitle)
    mem = _memory_prices(q, ftitle, strict) if fetch is None else None     # injected fetch (tests) bypasses memory
    if mem:
        prices, info = mem
        med0 = quantile(prices, 0.5)
        prices = sorted(p for p in prices if med0 / 3 <= p <= med0 * 3)
        base = {"query": q, "n": len(prices), "basis": "sold", "fetched_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
                "source": f"market memory ({info['product_key']}, eBay.de sold, ≤{int(os.environ.get('MEM_MAX_AGE_SOLD_H', '72'))}h)",
                "cache_hit": "memory", "lookup_ms": info["lookup_ms"]}
        return _finish(prices, condition, base)
    cache_p = sell_dir / "comps_cache.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    hit = cache.get(q)
    if hit and time.time() - hit["fetched_at"] < CACHE_TTL_S:
        raw, fetched = hit["raw"], hit["fetched_at"]
    else:
        try:
            raw = (fetch or _fetch_sold)(q, min_price)
        except Exception as e:
            return {"status": "error", "reason": f"comps_fetch_failed:{type(e).__name__}", "query": q}
        fetched = time.time()
        # cache titles+prices only (no seller fields, Art III)
        raw = [{"title": str(i.get("title", ""))[:140], "soldPrice": i.get("soldPrice"),
                "soldCurrency": i.get("soldCurrency"), "endedAt": i.get("endedAt")} for i in raw]
        cache[q] = {"fetched_at": fetched, "raw": raw}
        cache_p.write_text(json.dumps(cache, ensure_ascii=False))
        if fetch is None:
            _memory_writeback(q, raw)                     # scraped once => remembered (US-10 write-back)
    cands = [{"title": i["title"], "price": notice._safe_float(i["soldPrice"])} for i in raw
             if i.get("soldPrice") and i.get("soldCurrency") in (None, "EUR")
             and not EXCLUDE_ALWAYS.search(i["title"]) and not notice.DEFECT_RE.search(i["title"])]
    grounded = rerank.filter_grounded_comps(q, cands, min_confidence=0.75)
    # model grounding (bug found via US-10 memory comparison, Sat 26 Sep): word-overlap alone lets
    # "iPhone 14 Pro Max" sales price a plain "iPhone 14" (+€60 median). A comp whose product key is a
    # DIFFERENT known key is dropped; unkeyable comp titles are kept (overlap already vetted them).
    from ..memory import keys as mkeys
    qkey = mkeys.rules_key(q)
    if qkey:
        grounded = [c for c in grounded if mkeys.rules_key(c["title"]) in (None, qkey)]
    grounded, want = facet_filter(ftitle, grounded, strict)
    # chip tier: a "Pro" query must not be priced with "Max" sales and vice versa (same RAM, ~€1k apart)
    tier = re.search(r"\bm\d\s*(pro|max|ultra)\b", ftitle, re.I)
    if tier:
        tq = tier.group(1).lower()
        grounded = [c for c in grounded if (m := re.search(r"\bm\d\s*(pro|max|ultra)\b", c["title"], re.I)) is None
                    or m.group(1).lower() == tq]
        want = {**want, "chip_tier": tq}
    grounded = variant_filter(ftitle, grounded)
    prices = sorted(c["price"] for c in grounded if c["price"] > 0)
    # drop extreme outliers (bundles / lots) beyond 3x median
    if prices:
        med0 = quantile(prices, 0.5)
        prices = [p for p in prices if med0 / 3 <= p <= med0 * 3]
    base = {"query": q, "n": len(prices), "basis": "sold", "fetched_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(fetched)),
            "source": f"{os.environ.get('APIFY_ACTOR_SOLD', 'caffein.dev/ebay-sold-listings')} [ebay.de, sold 30d, used]",
            "facets": want}
    return _finish(prices, condition, base)


def _finish(prices: list[float], condition: str, base: dict) -> dict:
    """Shared tail for memory and scraped paths: fail-closed on thin data, condition-adjusted P60/P40."""
    if len(prices) < MIN_SALES:
        return {**base, "status": "no_comps", "reason": f"only_{len(prices)}_grounded_sales"}
    f = CONDITION_FACTOR.get(condition, CONDITION_FACTOR["unknown"])
    p40, med, p60 = quantile(prices, FLOOR_Q), quantile(prices, 0.5), quantile(prices, ASK_Q)
    ask, floor = round_price(p60 * f), round_price(p40 * f)
    if floor >= ask:
        # tight market (P40≈P60 round to the same step): floor = one rounding step below ask, not a flat -15%
        step = 1 if ask < 50 else 5 if ask < 200 else 10
        floor = max(step, ask - step)
    return {**base, "status": "ok", "ask": ask, "floor": floor, "median": round(med, 2), "p40": round(p40, 2),
            "p60": round(p60, 2), "condition_factor": f,
            "samples": [round(p, 2) for p in prices][:40]}
