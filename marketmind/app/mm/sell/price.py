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


def price(query: str, condition: str, sell_dir: Path, fetch=None, min_price: int = 5) -> dict:
    """Returns {status: ok|no_comps|error, ask, floor, median, p40, p60, n, basis, source, query, samples}."""
    q = " ".join((query or "").lower().split())[:80]
    if len(q) < 3:
        return {"status": "no_comps", "reason": "empty_query", "query": q}
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
    cands = [{"title": i["title"], "price": notice._safe_float(i["soldPrice"])} for i in raw
             if i.get("soldPrice") and i.get("soldCurrency") in (None, "EUR")
             and not EXCLUDE_ALWAYS.search(i["title"]) and not notice.DEFECT_RE.search(i["title"])]
    grounded = rerank.filter_grounded_comps(q, cands, min_confidence=0.75)
    prices = sorted(c["price"] for c in grounded if c["price"] > 0)
    # drop extreme outliers (bundles / lots) beyond 3x median
    if prices:
        med0 = quantile(prices, 0.5)
        prices = [p for p in prices if med0 / 3 <= p <= med0 * 3]
    base = {"query": q, "n": len(prices), "basis": "sold", "fetched_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(fetched)),
            "source": f"{os.environ.get('APIFY_ACTOR_SOLD', 'caffein.dev/ebay-sold-listings')} [ebay.de, sold 30d, used]"}
    if len(prices) < MIN_SALES:
        return {**base, "status": "no_comps", "reason": f"only_{len(prices)}_grounded_sales"}
    f = CONDITION_FACTOR.get(condition, CONDITION_FACTOR["unknown"])
    p40, med, p60 = quantile(prices, FLOOR_Q), quantile(prices, 0.5), quantile(prices, ASK_Q)
    ask, floor = round_price(p60 * f), round_price(p40 * f)
    if floor >= ask:
        floor = round_price(ask * 0.85)
    return {**base, "status": "ok", "ask": ask, "floor": floor, "median": round(med, 2), "p40": round(p40, 2),
            "p60": round(p60, 2), "condition_factor": f,
            "samples": [round(p, 2) for p in prices][:40]}
