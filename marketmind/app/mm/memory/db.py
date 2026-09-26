"""MARKET MEMORY (US-10) — local SQLite store for prices, verdicts, fetch cadence and human feedback.

Why SQLite: ~12k fetched rows/day (99% repeats) is tiny; stdlib-only (Art XI), in-process, sub-ms indexed
reads, WAL so the loop, sell CLI and backfill can read concurrently. Schema is append-mostly and
ClickHouse/DuckDB-portable (no triggers, no FK cascades, ISO-8601 UTC text timestamps, REAL prices).
Privacy (Art III): no seller or buyer fields exist in any table — ingest drops them.
"""
from __future__ import annotations
import os, sqlite3, time
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
DEFAULT_DB = APP / "out" / "market.db"
SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);

-- every Marktplaats listing ever seen (content only). disappeared_at => time-on-market.
CREATE TABLE IF NOT EXISTS listings (
  listing_id     TEXT PRIMARY KEY,
  platform       TEXT NOT NULL DEFAULT 'marktplaats.nl',
  title          TEXT NOT NULL,
  title_norm     TEXT NOT NULL,
  product_key    TEXT,
  price_eur      REAL,
  price_type     TEXT,
  condition      TEXT,
  search_query   TEXT,
  first_seen     TEXT NOT NULL,
  last_seen      TEXT NOT NULL,
  seen_count     INTEGER NOT NULL DEFAULT 1,
  disappeared_at TEXT,
  text_hash      TEXT,
  photo_dhash    TEXT
);
CREATE INDEX IF NOT EXISTS ix_listings_key ON listings(product_key, last_seen);
CREATE INDEX IF NOT EXISTS ix_listings_text ON listings(text_hash);
CREATE INDEX IF NOT EXISTS ix_listings_query ON listings(search_query, first_seen);

-- price observations per product key, labelled by source/basis. Never mixed silently.
CREATE TABLE IF NOT EXISTS price_obs (
  obs_id       INTEGER PRIMARY KEY AUTOINCREMENT,
  product_key  TEXT NOT NULL,
  source       TEXT NOT NULL CHECK (source IN ('mp_ask','ebay_sold','ebay_ask','own_sale')),
  price_eur    REAL NOT NULL CHECK (price_eur > 0),
  observed_at  TEXT NOT NULL,
  ref          TEXT,               -- external item id (dedupe key per source), never a person
  title        TEXT,
  UNIQUE (source, ref)
);
CREATE INDEX IF NOT EXISTS ix_obs_key ON price_obs(product_key, source, observed_at);

-- T27 verdict cache: a re-post (same text hash or near photo) reuses the prior verdict.
CREATE TABLE IF NOT EXISTS verdicts (
  text_hash    TEXT PRIMARY KEY,
  photo_dhash  TEXT,
  listing_id   TEXT NOT NULL,
  action       TEXT NOT NULL,
  reason_codes TEXT NOT NULL,
  gate         TEXT NOT NULL,
  price_eur    REAL,
  decided_at   TEXT NOT NULL,
  hits         INTEGER NOT NULL DEFAULT 0
);

-- one row per (run, query): drives the learned fetch cadence.
CREATE TABLE IF NOT EXISTS fetches (
  fetch_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  search_query TEXT NOT NULL,
  fetched_at   TEXT NOT NULL,
  hour_local   INTEGER NOT NULL,
  n_fetched    INTEGER NOT NULL,
  n_new        INTEGER NOT NULL,
  cost_usd     REAL,
  run_ref      TEXT,
  UNIQUE (run_ref, search_query)
);
CREATE INDEX IF NOT EXISTS ix_fetches_q ON fetches(search_query, fetched_at);

-- human corrections and outcomes (the "memory of being corrected").
CREATE TABLE IF NOT EXISTS feedback (
  fb_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  kind         TEXT NOT NULL CHECK (kind IN ('model_id','price_override','offer_outcome','draft_confirm','verdict_override')),
  subject      TEXT NOT NULL,      -- listing/item id or photo dhash
  proposed     TEXT,
  corrected    TEXT,
  product_key  TEXT,
  at           TEXT NOT NULL,
  actor        TEXT NOT NULL DEFAULT 'human'
);
CREATE INDEX IF NOT EXISTS ix_fb_kind ON feedback(kind, subject);

-- title -> product key cache (deterministic normalizer or JEV proposal)
CREATE TABLE IF NOT EXISTS product_keys (
  title_norm   TEXT PRIMARY KEY,
  product_key  TEXT,               -- NULL = 'none' (explicitly unkeyable)
  method       TEXT NOT NULL CHECK (method IN ('rules','jev','human')),
  confidence   REAL,
  at           TEXT NOT NULL,
  hits         INTEGER NOT NULL DEFAULT 0
);

-- lookup telemetry for the before/after benchmark
CREATE TABLE IF NOT EXISTS lookups (
  lk_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  kind         TEXT NOT NULL,      -- comps | verdict | product_key
  hit          INTEGER NOT NULL,   -- 1 = answered from memory
  ms           REAL NOT NULL,
  at           TEXT NOT NULL,
  detail       TEXT
);

-- Apify runs already ingested (sync cursor; dataset reads only, never re-downloaded)
CREATE TABLE IF NOT EXISTS synced_runs (
  run_id       TEXT PRIMARY KEY,
  actor        TEXT NOT NULL,
  at           TEXT NOT NULL
);
"""


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def connect(path: str | Path | None = None, readonly: bool = False) -> sqlite3.Connection:
    p = Path(path or os.environ.get("MARKET_DB") or DEFAULT_DB)
    if readonly:
        if not p.exists():
            raise FileNotFoundError(p)
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=5)
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(p, timeout=10)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.executescript(SCHEMA)
        con.execute("INSERT OR IGNORE INTO meta(k, v) VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
        con.commit()
    con.row_factory = sqlite3.Row
    return con
