#!/usr/bin/env python3
"""Backfill / incremental sync of out/market.db from EXISTING Apify run datasets (dataset reads only —
never starts a scraping run, so it costs no Apify compute).

Replays runs in chronological order so first_seen / n_new / cadence stats are what the live loop saw:
  haketa/marktplaats-scraper      -> listings + mp_ask obs + fetches (per query, with run cost)
  caffein.dev/ebay-sold-listings  -> ebay_sold obs
  automation-lab/ebay-scraper     -> ebay_ask obs
Idempotent and incremental: `synced_runs` is the cursor (each run's dataset is read once).
Usage: python3 tools/backfill_memory.py [--since 2026-09-26] [--db path] [--quiet]
"""
from __future__ import annotations
import argparse, json, os, sys, time, urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
for l in (APP / ".env").read_text().splitlines():
    if "=" in l and not l.lstrip().startswith("#"):
        k, v = l.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
from mm.memory import db, store  # noqa: E402

API = "https://api.apify.com/v2"


def get(path: str):
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {os.environ['APFY_TOKEN']}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def runs(actor: str, since: str) -> list[dict]:
    items = get(f"/acts/{actor.replace('/', '~')}/runs?desc=1&limit=1000")["data"]["items"]
    return sorted([r for r in items if r["startedAt"] >= since and r["status"] == "SUCCEEDED"], key=lambda r: r["startedAt"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-09-26")
    ap.add_argument("--db", default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    con = db.connect(a.db)
    t0 = time.time()
    done = {r[0] for r in con.execute("SELECT run_id FROM synced_runs")} | \
           {r[0] for r in con.execute("SELECT DISTINCT run_ref FROM fetches WHERE run_ref IS NOT NULL")}
    stats: dict[str, float] = {"mp_runs": 0, "mp_items": 0, "mp_new": 0, "sold_runs": 0, "sold_obs": 0,
                               "ask_runs": 0, "ask_obs": 0, "skipped_runs": 0}

    def mark(run_id: str, actor: str) -> None:
        con.execute("INSERT OR IGNORE INTO synced_runs(run_id, actor, at) VALUES (?,?,?)", (run_id, actor, db.now_iso()))
        con.commit()

    listings_actor = os.environ.get("APIFY_ACTOR_LISTINGS", "haketa/marktplaats-scraper")
    for r in runs(listings_actor, a.since):
        if r["id"] in done:
            stats["skipped_runs"] += 1
            continue
        items = get(f"/datasets/{r['defaultDatasetId']}/items?clean=true&omit=images,attributes,description")
        at = (r.get("finishedAt") or r["startedAt"])[:19] + "Z"
        res = store.ingest_listings(con, items, run_ref=r["id"], cost_usd=r.get("usageTotalUsd"), at=at)
        mark(r["id"], listings_actor)
        stats["mp_runs"] += 1
        stats["mp_items"] += res["fetched"]
        stats["mp_new"] += res["new"]

    for actor, basis, key in (("caffein.dev/ebay-sold-listings", "ebay_sold", "sold"),
                              (os.environ.get("APIFY_ACTOR_COMPS", "automation-lab/ebay-scraper"), "ebay_ask", "ask")):
        for r in runs(actor, a.since):
            if r["id"] in done:
                stats["skipped_runs"] += 1
                continue
            items = get(f"/datasets/{r['defaultDatasetId']}/items?clean=true")
            at = (r.get("finishedAt") or r["startedAt"])[:19] + "Z"
            stats[f"{key}_obs"] += store.ingest_ebay(con, items, basis=basis, product_key=None, at=at)
            stats[f"{key}_runs"] += 1
            mark(r["id"], actor)

    q = lambda s: con.execute(s).fetchone()[0]   # noqa: E731
    stats.update({"listings": q("SELECT COUNT(*) FROM listings"),
                  "keyed_listings": q("SELECT COUNT(*) FROM listings WHERE product_key IS NOT NULL"),
                  "price_obs": q("SELECT COUNT(*) FROM price_obs"),
                  "product_keys": q("SELECT COUNT(DISTINCT product_key) FROM price_obs"),
                  "fetch_rows": q("SELECT COUNT(*) FROM fetches"), "seconds": round(time.time() - t0, 1)})
    print(json.dumps(stats) if a.quiet else json.dumps(stats, indent=1))
    if not a.quiet:
        for row in con.execute("SELECT product_key, source, COUNT(*) n, ROUND(AVG(price_eur),0) avg FROM price_obs "
                               "GROUP BY product_key, source HAVING n >= 3 ORDER BY n DESC LIMIT 25"):
            print(f"  {row[0]:24} {row[1]:10} n={row[2]:<4} avg €{row[3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
