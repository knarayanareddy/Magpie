"""STORE — ingest, DB-first comps, verdict cache, learned fetch cadence, feedback (US-10).

Every read that answers from memory records a `lookups` row (hit, ms) so the before/after benchmark
is measured, not claimed. All thresholds are env-tunable and conservative; memory never answers with
fewer than MEM_MIN_OBS observations of the REQUESTED basis (sold is never padded with asking prices).
"""
from __future__ import annotations
import hashlib, json, os, time
from datetime import datetime, timezone

from . import keys
from .db import now_iso

MIN_OBS = int(os.environ.get("MEM_MIN_OBS", "5"))
MAX_AGE_H = {"ebay_sold": float(os.environ.get("MEM_MAX_AGE_SOLD_H", "72")),   # sold prices move slowly
             "ebay_ask": float(os.environ.get("MEM_MAX_AGE_ASK_H", "24")),
             "mp_ask": float(os.environ.get("MEM_MAX_AGE_MP_H", "72")),
             "own_sale": 24 * 90}
SELLER_FIELDS = ("sellerName", "sellerId", "sellerType", "sellerUsername", "sellerFeedbackPercent",
                 "sellerFeedbackScore", "sellerPositivePercent", "sellerFeedbackCount", "location")


def _f(v) -> float | None:
    try:
        x = float(str(v).replace("€", "").replace(",", ".").strip())
        return x if x > 0 else None
    except (TypeError, ValueError):
        return None


def text_hash(title: str, description: str = "") -> str:
    """Re-post fingerprint: normalized title + first 300 normalized description chars."""
    return hashlib.sha256((keys.norm(title) + "|" + keys.norm(description)[:300]).encode()).hexdigest()[:16]


def _lookup(con, kind: str, hit: bool, t0: float, detail: str = "") -> float:
    ms = (time.perf_counter() - t0) * 1000
    con.execute("INSERT INTO lookups(kind, hit, ms, at, detail) VALUES (?,?,?,?,?)",
                (kind, int(hit), round(ms, 3), now_iso(), detail[:120]))
    return ms


# ---------------------------------------------------------------- ingest (writes)

def ingest_listings(con, raw_items: list[dict], *, run_ref: str | None = None, cost_usd: float | None = None,
                    at: str | None = None, use_jev: bool = False) -> dict:
    """Upsert Marktplaats actor items (seller fields dropped), add mp_ask price obs, record per-query fetch
    stats. Returns {fetched, new, by_query}. Idempotent per (listing, run)."""
    at = at or now_iso()
    hour = datetime.fromisoformat(at.replace("Z", "+00:00")).astimezone().hour
    by_q: dict[str, list[int]] = {}
    for it in raw_items:
        it = {k: v for k, v in it.items() if k not in SELLER_FIELDS}          # Art III at the boundary
        lid = str(it.get("listingId") or it.get("id") or "")
        title = str(it.get("title") or "")
        if not lid or not title:
            continue
        q = str(it.get("searchQuery") or "")
        price = _f(it.get("price"))
        key, _ = keys.resolve(con, title, use_jev=use_jev)
        th = text_hash(title, str(it.get("description") or ""))
        cur = con.execute("SELECT last_seen FROM listings WHERE listing_id=?", (lid,)).fetchone()
        if cur is None:
            con.execute("""INSERT INTO listings(listing_id, title, title_norm, product_key, price_eur, price_type,
                           condition, search_query, first_seen, last_seen, text_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (lid, title[:200], keys.norm(title), key, price, it.get("priceType"), it.get("condition"),
                         q, at, at, th))
            by_q.setdefault(q, [0, 0])[1] += 1
        else:
            if at > cur["last_seen"]:
                con.execute("UPDATE listings SET last_seen=?, seen_count=seen_count+1, price_eur=COALESCE(?, price_eur), "
                            "disappeared_at=NULL WHERE listing_id=?", (at, price, lid))
        by_q.setdefault(q, [0, 0])[0] += 1
        # 'Bieden' listings often carry placeholder prices (€1, €0): only fixed prices, or bidding ≥ €20, count
        if key and price and (it.get("priceType") != "bidding" or price >= 20):
            con.execute("INSERT OR IGNORE INTO price_obs(product_key, source, price_eur, observed_at, ref, title) "
                        "VALUES (?,?,?,?,?,?)", (key, "mp_ask", price, at, f"{lid}@{price}", title[:140]))
    per_q_cost = (cost_usd / len(by_q)) if (cost_usd and by_q) else None
    for q, (n, new) in by_q.items():
        con.execute("INSERT OR IGNORE INTO fetches(search_query, fetched_at, hour_local, n_fetched, n_new, cost_usd, run_ref) "
                    "VALUES (?,?,?,?,?,?,?)", (q, at, hour, n, new, per_q_cost, run_ref))
    con.commit()
    return {"fetched": sum(v[0] for v in by_q.values()), "new": sum(v[1] for v in by_q.values()),
            "by_query": {q: {"fetched": v[0], "new": v[1]} for q, v in by_q.items()}}


def mark_disappeared(con, query: str, seen_ids: set[str], at: str | None = None) -> int:
    """Listings of `query` not in the latest full fetch are marked gone once (=> time-on-market)."""
    at = at or now_iso()
    rows = con.execute("SELECT listing_id FROM listings WHERE search_query=? AND disappeared_at IS NULL", (query,)).fetchall()
    gone = [r[0] for r in rows if r[0] not in seen_ids]
    con.executemany("UPDATE listings SET disappeared_at=? WHERE listing_id=?", [(at, g) for g in gone])
    con.commit()
    return len(gone)


def ingest_ebay(con, raw_items: list[dict], *, basis: str, product_key: str | None = None,
                at: str | None = None) -> int:
    """eBay sold (caffein.dev: soldPrice/endedAt/itemId) or asking (automation-lab: price/itemId) items.
    product_key forced by caller (the query it was fetched for) or resolved from the title."""
    assert basis in ("ebay_sold", "ebay_ask")
    from .. import notice                           # DEFECT_RE: single source with the buy side
    at = at or now_iso()
    n = 0
    for it in raw_items:
        title = str(it.get("title") or "")
        if notice.DEFECT_RE.search(title):
            continue                                  # a broken unit's price is not a market price
        price = _f(it.get("soldPrice") if basis == "ebay_sold" else it.get("price"))
        cur = it.get("soldCurrency") or it.get("currency") or "EUR"
        if not price or cur not in ("EUR", None):
            continue
        key = keys.rules_key(title) or None
        if product_key and key and key != product_key:
            continue                                  # grounded: an iPhone 14 Pro sale never lands in 'iphone 14'
        key = key or product_key
        if not key:
            continue
        observed = (str(it.get("endedAt")) + "T12:00:00Z") if basis == "ebay_sold" and it.get("endedAt") else at
        n += con.execute("INSERT OR IGNORE INTO price_obs(product_key, source, price_eur, observed_at, ref, title) "
                         "VALUES (?,?,?,?,?,?)", (key, basis, price, observed, str(it.get("itemId") or title)[:60],
                                                   title[:140])).rowcount
    con.commit()
    return n


def record_own_sale(con, product_key: str, price_eur: float, ref: str) -> None:
    con.execute("INSERT OR IGNORE INTO price_obs(product_key, source, price_eur, observed_at, ref, title) VALUES (?,?,?,?,?,?)",
                (product_key, "own_sale", price_eur, now_iso(), ref, None))
    con.commit()


# ---------------------------------------------------------------- DB-first comps (read)

def _median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def fresh_obs(con, product_key: str, basis: str, max_age_h: float | None = None) -> list[tuple[float, str]]:
    """Raw fresh (price, title) observations of ONE basis for a key — for callers that need quantiles."""
    age = max_age_h if max_age_h is not None else MAX_AGE_H.get(basis, 24)
    cutoff = datetime.fromtimestamp(time.time() - age * 3600, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [(r[0], r[1] or "") for r in con.execute(
        "SELECT price_eur, title FROM price_obs WHERE product_key=? AND source=? AND observed_at>=?",
        (product_key, basis, cutoff))]


def comps(con, product_key: str | None, basis: str = "ebay_sold", *, min_obs: int = MIN_OBS,
          max_age_h: float | None = None, record: bool = True) -> dict | None:
    """Memory answer or None (=> caller scrapes and writes back). Median/MAD over fresh obs of ONE basis,
    3×-median outlier trim (lots/bundles). Returned dict is labelled source=memory with n and age."""
    t0 = time.perf_counter()
    if not product_key:
        if record:
            _lookup(con, "comps", False, t0, "no_key")
        return None
    age = max_age_h if max_age_h is not None else MAX_AGE_H.get(basis, 24)
    cutoff = datetime.fromtimestamp(time.time() - age * 3600, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = con.execute("SELECT price_eur, observed_at FROM price_obs WHERE product_key=? AND source=? AND observed_at>=?",
                       (product_key, basis, cutoff)).fetchall()
    prices = [r[0] for r in rows]
    if prices:
        m0 = _median(prices)
        prices = [p for p in prices if m0 / 3 <= p <= m0 * 3]
    if len(prices) < min_obs:
        if record:
            _lookup(con, "comps", False, t0, f"{product_key}|{basis}|n={len(prices)}")
            con.commit()
        return None
    med = _median(prices)
    mad = _median([abs(p - med) for p in prices]) or 1.0
    newest = max(r[1] for r in rows)
    age_h = (time.time() - datetime.fromisoformat(newest.replace("Z", "+00:00")).timestamp()) / 3600
    out = {"median": round(med, 2), "mad": round(mad, 2), "n": len(prices), "basis": basis.replace("ebay_", ""),
           "source": "memory", "product_key": product_key, "age_h": round(max(age_h, 0.0), 1)}
    if record:
        out["lookup_ms"] = round(_lookup(con, "comps", True, t0, f"{product_key}|{basis}|n={len(prices)}"), 3)
        con.commit()
    return out


# ---------------------------------------------------------------- T27 verdict cache

def verdict_get(con, title: str, description: str = "", price: float | None = None) -> dict | None:
    """Prior verdict for a re-post. Only reused if the price did not DROP (a cheaper re-post is a new decision)."""
    t0 = time.perf_counter()
    th = text_hash(title, description)
    r = con.execute("SELECT * FROM verdicts WHERE text_hash=?", (th,)).fetchone()
    hit = bool(r) and (price is None or r["price_eur"] is None or price >= r["price_eur"])
    if hit:
        con.execute("UPDATE verdicts SET hits=hits+1 WHERE text_hash=?", (th,))
    _lookup(con, "verdict", hit, t0, th)
    con.commit()
    if not hit:
        return None
    return {"action": r["action"], "reason_codes": json.loads(r["reason_codes"]), "gate": r["gate"],
            "listing_id": r["listing_id"], "decided_at": r["decided_at"], "cache_hit": "verdict"}


def verdict_put(con, title: str, description: str, listing_id: str, action: str, reasons: list[str],
                gate: str, price: float | None) -> None:
    con.execute("INSERT OR REPLACE INTO verdicts(text_hash, listing_id, action, reason_codes, gate, price_eur, decided_at) "
                "VALUES (?,?,?,?,?,?,?)", (text_hash(title, description), listing_id, action, json.dumps(reasons),
                                           gate, price, now_iso()))
    con.commit()


# ---------------------------------------------------------------- learned fetch cadence (procedure)

CADENCE_MIN_S = int(os.environ.get("MEM_CADENCE_MIN_S", "300"))
CADENCE_MAX_S = int(os.environ.get("MEM_CADENCE_MAX_S", "3600"))


def cadence(con, query: str, hour_local: int, *, days: int = 7) -> dict:
    """Seconds between fetches for (query, hour). Rate = new listings per fetch in this hour-of-day over the
    last `days` (Laplace-smoothed toward 'something new'); expected-new-per-fetch ≥ 0.5 => 5 min, falling
    toward the 60-min cap as the hour proves empty. Fewer than 3 observations => 5 min (no evidence, no skip)."""
    since = datetime.fromtimestamp(time.time() - days * 86400, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = con.execute("SELECT COUNT(*) n, COALESCE(SUM(n_new),0) new FROM fetches WHERE search_query=? AND hour_local=? "
                    "AND fetched_at>=?", (query, hour_local, since)).fetchone()
    n, new = r["n"], r["new"]
    if n < 3:
        return {"interval_s": CADENCE_MIN_S, "why": f"only {n} fetches seen at {hour_local:02d}h — default", "rate": None}
    rate = (new + 0.5) / (n + 1)                          # expected new listings per fetch
    interval = CADENCE_MIN_S if rate >= 0.5 else min(CADENCE_MAX_S, int(CADENCE_MIN_S * 0.5 / max(rate, 1e-3)))
    interval = max(CADENCE_MIN_S, (interval // 60) * 60)
    return {"interval_s": interval, "rate": round(rate, 3),
            "why": f"{new} new in {n} fetches at {hour_local:02d}h (7d) → every {interval // 60} min"}


def due(con, query: str, now_ts: float | None = None) -> tuple[bool, dict]:
    """Is `query` due for a fetch now? Any new listing in the last fetch resets to the minimum cadence."""
    now_ts = now_ts or time.time()
    hour = datetime.fromtimestamp(now_ts).hour
    c = cadence(con, query, hour)
    now_iso_ = datetime.fromtimestamp(now_ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    last = con.execute("SELECT fetched_at, n_new FROM fetches WHERE search_query=? AND fetched_at<=? "
                       "ORDER BY fetched_at DESC LIMIT 1", (query, now_iso_)).fetchone()
    if not last:
        return True, {**c, "why": "never fetched"}
    if last["n_new"] > 0:
        c = {**c, "interval_s": CADENCE_MIN_S, "why": f"last fetch had {last['n_new']} new → hot, 5 min"}
    since = now_ts - datetime.fromisoformat(last["fetched_at"].replace("Z", "+00:00")).timestamp()
    return since >= c["interval_s"] - 5, {**c, "since_s": int(since)}


# ---------------------------------------------------------------- feedback (memory of corrections)

def feedback(con, kind: str, subject: str, proposed=None, corrected=None, product_key: str | None = None,
             actor: str = "human") -> None:
    con.execute("INSERT INTO feedback(kind, subject, proposed, corrected, product_key, at, actor) VALUES (?,?,?,?,?,?,?)",
                (kind, subject, None if proposed is None else json.dumps(proposed, ensure_ascii=False),
                 None if corrected is None else json.dumps(corrected, ensure_ascii=False), product_key, now_iso(), actor))
    if kind == "model_id" and corrected:
        # teach the key cache: this vision label / title now maps to the human's model
        k = keys.rules_key(str(corrected))
        if k:
            con.execute("INSERT OR REPLACE INTO product_keys(title_norm, product_key, method, confidence, at) VALUES (?,?,?,?,?)",
                        (keys.norm(str(proposed or "")), k, "human", 1.0, now_iso()))
    con.commit()


def correction_hint(con, photo_dhash: str | None, max_hamming: int = 10) -> dict | None:
    """Memory of being corrected: if a near-identical photo was previously re-labelled by the human, surface it."""
    if not photo_dhash:
        return None
    from .. import phash
    for r in con.execute("SELECT subject, corrected, at FROM feedback WHERE kind='model_id' ORDER BY at DESC LIMIT 500"):
        s = r["subject"]
        if len(s) == 16 and all(c in "0123456789abcdef" for c in s) and phash.hamming(s, photo_dhash) <= max_hamming:
            return {"model": json.loads(r["corrected"]), "at": r["at"], "cache_hit": "correction"}
    return None
