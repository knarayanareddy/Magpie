"""LIVE ADAPTER — the only surface the buy loop touches (US-10). Every call is fail-OPEN to legacy
behaviour: if the store is missing, locked or broken, the loop behaves exactly as before memory existed.

Flags (all default ON in live mode, set =0 to disable; sim/selftest never uses memory):
  MEM_INGEST   passive: every live fetch -> listings / mp_ask obs / per-query fetch stats (drives cadence)
  MEM_COMPS    per-item product-key comps from memory (eBay sold, >=5 fresh obs) ahead of family comps
  MEM_VERDICT  T27: a re-post (same normalized text, price not dropped) reuses the prior skip/escalate verdict
  MEM_CADENCE  learned per-query fetch cadence (5-60 min); a skipped query costs no Apify run
Guards: models never touch this path; policy.py is untouched (the gate still decides on the facts);
a cached PURSUE is never replayed (a re-post of something we already offered on escalates instead).
"""
from __future__ import annotations
import os, sys, time, traceback

_WARNED: set[str] = set()
_STATS = {"comps_hits": 0, "comps_miss": 0, "verdict_hits": 0, "cadence_skipped": 0, "cadence_fetched": 0,
          "ingested": 0, "errors": 0}


def enabled(flag: str, mode: str) -> bool:
    return mode == "live" and os.environ.get("MEM_" + flag, "1") == "1" and os.environ.get("MEM_ALL", "1") == "1"


def _warn(where: str) -> None:
    _STATS["errors"] += 1
    if where not in _WARNED:                      # one line per failure site, never spam the daemon log
        _WARNED.add(where)
        print(f"[memory] {where} failed — falling back to legacy path: {traceback.format_exc(limit=1).strip().splitlines()[-1]}",
              file=sys.stderr)


_CON = None


def _con():
    global _CON
    if _CON is None:
        from .db import connect
        _CON = connect()
    return _CON


def reset_cycle_stats() -> dict:
    snap = dict(_STATS)
    for k in _STATS:
        _STATS[k] = 0
    return snap


def _bump(con, key: str, n: int) -> None:
    """Persistent counters in meta (survive restarts) — the 'after' side of the before/after benchmark."""
    con.execute("INSERT OR IGNORE INTO meta(k, v) VALUES (?, '0')", (key,))
    con.execute("UPDATE meta SET v = CAST(CAST(v AS INTEGER) + ? AS TEXT) WHERE k = ?", (int(n), key))
    con.commit()


# ---------------------------------------------------------------- cadence (before fetching)

def due_queries(queries: list[str], mode: str) -> tuple[list[str], dict]:
    """Subset of queries due this cycle. Fail-open: any error => all queries (legacy behaviour)."""
    if not enabled("CADENCE", mode):
        return list(queries), {}
    try:
        from . import store
        con = _con()
        due, why = [], {}
        for q in queries:
            ok, info = store.due(con, q)
            why[q] = {"due": ok, "interval_min": info["interval_s"] // 60, "since_s": info.get("since_s"),
                      "why": info["why"]}
            (due.append(q) if ok else None)
        _STATS["cadence_fetched"] += len(due)
        _STATS["cadence_skipped"] += len(queries) - len(due)
        _bump(con, "cadence_skipped_total", len(queries) - len(due))
        _bump(con, "cadence_planned_total", len(queries))
        return due, why
    except Exception:
        _warn("cadence")
        return list(queries), {}


# ---------------------------------------------------------------- passive ingest (after fetching)

def ingest(raw_items: list[dict], mode: str, *, queries_fetched: list[str]) -> None:
    """Record the live fetch. Queries that returned nothing still get a fetch row (n=0) so cadence learns."""
    if not enabled("INGEST", mode):
        return
    try:
        from . import store
        from .db import now_iso
        con = _con()
        at = now_iso()
        if not con.execute("SELECT 1 FROM meta WHERE k='live_ingest_since'").fetchone():
            con.execute("INSERT INTO meta(k, v) VALUES ('live_ingest_since', ?)", (at,))
        usd = float(os.environ.get("APIFY_USD_PER_LISTINGS_RUN", "0.0196"))   # measured Sat mean; labelled estimate
        res = store.ingest_listings(con, raw_items, run_ref=f"live:{at}", cost_usd=usd * len(queries_fetched), at=at)
        hour = time.localtime().tm_hour
        for q in queries_fetched:                  # zero-result / mis-attributed queries: explicit empty fetch row
            if q not in res["by_query"]:
                con.execute("INSERT OR IGNORE INTO fetches(search_query, fetched_at, hour_local, n_fetched, n_new, cost_usd, run_ref) "
                            "VALUES (?,?,?,?,?,?,?)", (q, at, hour, len(raw_items), 0, usd, f"live:{at}"))
        con.commit()
        _STATS["ingested"] += res["fetched"]
    except Exception:
        _warn("ingest")


# ---------------------------------------------------------------- per-item comps

def item_comps(item: dict, mode: str) -> dict | None:
    """Product-key comps from memory (eBay sold only) or None => legacy family comps."""
    if not enabled("COMPS", mode):
        return None
    try:
        from . import keys, store
        key = keys.rules_key(item.get("title", ""))
        if not key:
            return None
        c = store.comps(_con(), key, "ebay_sold")
        _STATS["comps_hits" if c else "comps_miss"] += 1
        return c
    except Exception:
        _warn("comps")
        return None


def apply_comps(facts: dict, item: dict, mem: dict) -> dict:
    """Override family comps with finer product-key memory comps. The gate still decides (policy.py untouched).
    Condition asymmetry: memory comps are eBay 'used, working' sales — a listing that self-declares damage
    ('schade', 'barst', 'kras op scherm', …) is not comparable, so its margin is not computed from them
    (grounding_note=condition_mismatch => escalate for a human). Found in the Sat replay: '14 Pro Max, lichte
    schade €350' would have flipped from no_margin (family comps) to pursue."""
    from .. import decide                         # decide.skin = the policy oracle (single import path)
    price = item.get("price_eur")
    if has_damage(f"{item.get('title', '')} {item.get('description', '')}"):
        return {**facts, "comps": mem, "comps_key": mem["product_key"], "margin_z": None,
                "grounding_note": "condition_mismatch", "comps_source": "memory"}
    return {**facts, "comps": mem, "comps_key": mem["product_key"],
            "margin_z": decide.skin.margin_z(price, mem["median"], mem["mad"]),
            "grounding_note": None if price else "no_price", "comps_source": "memory"}


import re as _re
DAMAGE_RE = _re.compile(r"\b(schade|beschadigd|barst(je)?|gebarsten|kras(sen)?\s+(op|in)\s+(het\s+)?scherm|"
                        r"scherm\s*(kapot|gebroken|barst)|lichte\s+schade|waterschade|brandplek|deuk|"
                        r"cracked|damaged|broken|defect|kapot|werkt\s+niet|niet\s+werkend|icloud|simlock|"
                        r"accu\s*(slecht|vervangen\s+nodig)|batterij\s*(slecht|\d{2}\s*%\s*vervangen))\b", _re.I)
# negation (measured on the first live memory cycle: "nooit kapot geweest" flagged a clean phone):
# a hit preceded within 3 words by geen/nooit/niet/zonder/no/never, or followed by vrij/free, is not damage.
_NEG_BEFORE = _re.compile(r"\b(geen|nooit|niet|zonder|no|never|nie)\b(\s+\S+){0,3}\s*$", _re.I)
_NEG_AFTER = _re.compile(r"^\s*-?\s*(vrij|free|los|ontgrendeld)\b", _re.I)


def has_damage(text: str) -> bool:
    for m in DAMAGE_RE.finditer(text or ""):
        before, after = text[max(0, m.start() - 40):m.start()], text[m.end():m.end() + 14]
        if _NEG_BEFORE.search(before) or _NEG_AFTER.search(after):
            continue
        return True
    return False


# ---------------------------------------------------------------- T27 verdict cache

def prior_verdict(item: dict, mode: str) -> dict | None:
    if not enabled("VERDICT", mode):
        return None
    try:
        from . import store
        v = store.verdict_get(_con(), item.get("title", ""), item.get("description", ""), item.get("price_eur"))
        if v and v["listing_id"] != item.get("id"):
            _STATS["verdict_hits"] += 1
            return v
        return None
    except Exception:
        _warn("verdict_get")
        return None


def remember_verdict(item: dict, action: str, reasons: list[str], gate: str, mode: str) -> None:
    if not enabled("VERDICT", mode):
        return
    try:
        from . import store
        store.verdict_put(_con(), item.get("title", ""), item.get("description", ""), item["id"], action,
                          reasons, gate, item.get("price_eur"))
    except Exception:
        _warn("verdict_put")


def summary_line(stats: dict) -> str:
    """One mono digest line; empty when memory did nothing this cycle."""
    if not any(stats.values()):
        return ""
    usd = float(os.environ.get("APIFY_USD_PER_LISTINGS_RUN", "0.0196"))
    parts = [f"comps {stats['comps_hits']}/{stats['comps_hits'] + stats['comps_miss']} from memory"]
    if stats["verdict_hits"]:
        parts.append(f"{stats['verdict_hits']} re-post verdicts reused")
    if stats["cadence_skipped"]:
        parts.append(f"{stats['cadence_skipped']} fetches skipped by learned cadence (≈${stats['cadence_skipped'] * usd:.2f})")
    if stats["errors"]:
        parts.append(f"{stats['errors']} memory errors → legacy path")
    return "memory: " + " · ".join(parts)
