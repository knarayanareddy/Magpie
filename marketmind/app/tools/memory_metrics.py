#!/usr/bin/env python3
"""Before/after numbers for US-10 claims — every "learns"/"faster"/"cheaper" statement cites this output.

Reads out/market.db only (no network). Prints and writes out/memory_metrics.json:
  * Apify runs & $ per NEW listing (overall and per query) — the waste the cadence attacks
  * repeat rate (fetched listings that were already known)
  * memory lookups: hit rate + p50/p95 ms per kind (comps / verdict / product_key)
  * what the learned cadence WOULD do now: per query/hour interval and projected runs saved vs fixed 5-min
Usage: python3 tools/memory_metrics.py [--db path] [--window-h 24]
"""
from __future__ import annotations
import argparse, json, sys, time
from datetime import datetime, timezone
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from mm.memory import db, store  # noqa: E402


def pct(xs, q):
    s = sorted(xs)
    return round(s[min(len(s) - 1, int(len(s) * q))], 3) if s else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("--window-h", type=float, default=24)
    a = ap.parse_args()
    con = db.connect(a.db)
    since = datetime.fromtimestamp(time.time() - a.window_h * 3600, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    f = con.execute("SELECT COUNT(*) runs, COALESCE(SUM(n_fetched),0) fetched, COALESCE(SUM(n_new),0) new, "
                    "COALESCE(SUM(cost_usd),0) usd FROM fetches WHERE fetched_at>=?", (since,)).fetchone()
    per_q = [dict(r) for r in con.execute(
        "SELECT search_query q, COUNT(*) runs, SUM(n_new) new, ROUND(SUM(cost_usd),3) usd, "
        "ROUND(SUM(cost_usd)/MAX(SUM(n_new),1),3) usd_per_new FROM fetches WHERE fetched_at>=? AND search_query<>'' "
        "GROUP BY 1 HAVING runs>=10 ORDER BY runs DESC", (since,))]
    lk = {}
    for kind in ("comps", "verdict", "product_key"):
        rows = con.execute("SELECT hit, ms FROM lookups WHERE kind=? AND at>=?", (kind, since)).fetchall()
        if rows:
            hits = [r["ms"] for r in rows if r["hit"]]
            lk[kind] = {"n": len(rows), "hit_rate": round(len(hits) / len(rows), 3),
                        "hit_p50_ms": pct(hits, 0.5), "hit_p95_ms": pct(hits, 0.95)}
    kc = con.execute("SELECT method, COUNT(*) n, SUM(hits) hits FROM product_keys GROUP BY method").fetchall()
    # what the learned cadence would schedule, per active query, for every hour we have evidence for
    sched, saved = {}, 0
    for q in [r["q"] for r in per_q]:
        hours = [r[0] for r in con.execute("SELECT DISTINCT hour_local FROM fetches WHERE search_query=?", (q,))]
        sched[q] = {}
        for h in sorted(hours):
            c = store.cadence(con, q, h)
            sched[q][f"{h:02d}h"] = c["interval_s"] // 60
            saved += 12 - 3600 // c["interval_s"]          # runs/hour saved vs a fixed 5-min cadence
    out = {
        "window_h": a.window_h,
        "fetch": {"runs": f["runs"], "fetched": f["fetched"], "new": f["new"],
                  "repeat_rate": round(1 - f["new"] / f["fetched"], 3) if f["fetched"] else None,
                  "usd": round(f["usd"], 3), "runs_per_new": round(f["runs"] / max(f["new"], 1), 2),
                  "usd_per_new": round(f["usd"] / max(f["new"], 1), 4)},
        "per_query": per_q,
        "lookups": lk,
        "product_keys": {r["method"]: {"titles": r["n"], "hits": r["hits"]} for r in kc},
        "learned_cadence_min": sched,
        "projected_runs_saved_per_day_vs_fixed_5min": saved,
        "store": {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("listings", "price_obs", "verdicts", "fetches", "feedback", "product_keys")},
    }
    (APP / "out" / "memory_metrics.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
