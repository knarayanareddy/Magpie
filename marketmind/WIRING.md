# WIRING.md — turn the walking skeleton from `sim` to `live` (30–60 min with keys)

The pipeline is done and self-tested in **sim** mode (`app/run_walking_skeleton.py`). Live mode swaps four HTTP surfaces. Nothing else changes.

## 0) Human punch list (T04 — cannot be automated)
- [ ] `kickoff/consent.txt` signed by `NAMED_RESELLER` (else set `unset`, Art III.3)
- [ ] Dedicated demo Marktplaats account (NOT personal) + second account + 1 consented friend
- [ ] Post the 5 items per `kickoff/LISTING-PLAN.md`
- [ ] Freeze `kickoff/PREREGISTRATION.md` (fill date + name)
- [ ] `cp app/env.example app/.env` and fill as keys arrive

## 1) Apify (T05 — real data)
1. Create token at apify.com → account settings → API tokens → `APFY_TOKEN`.
2. Note actor ids (start with one, Marktplaats listings actor, e.g. `haketa/marktplaats-scraper` — verify availability Fri; fallback: any listing scraper with `{search, category, maxItems}` input):
   - `APIFY_ACTOR_LISTINGS` — new listings, niche keywords
   - `APIFY_ACTOR_COMPS` — eBay sold comps (e.g. `apify/ebay-scraper` w/ sold filter)
   - `APIFY_ACTOR_OWN` — your 5 listings (generic scraper on your profile page) *(M1, T12)*
   - `APIFY_ACTOR_VERIFY` — brand/model verification *(M2)*
3. Smoke: `python3 app/run_walking_skeleton.py --mode live --only scan` → prints items + **measured actor cycle time** (kills the 60s myth, T05).
4. Dataset item shape (the parser expects): `{id, url, title, description, price_eur, category, images[], seller{name, since, rating_count}, posted_at}` — map once in `app/mm/notice.py:_normalize`.
5. **Fallback for Long-Running Scrapes (>60s): The Async Polling Loop (Mohammed Belfellah Pattern)**
   - **The 60s Wall:** Synchronous calls (`POST /acts/{id}/run-sync-get-dataset-items`) drop with HTTP 504 Gateway Timeout or TCP socket termination if a scraper paginates deeply or solves captchas.
   - **The Mohammed Belfellah Decoupled Pattern:** When webhooks (Topology B) are unreachable (e.g. local n8n without a public ngrok/Cloudflare tunnel) and synchronous runs exceed 60s, decouple scraping into an outbound polling loop:
     ```
     [Schedule / Trigger]
            │
            ▼
     1. [POST /v2/acts/{actorId}/runs] (Start async run; returns runId & defaultDatasetId in ~100ms)
            │
            ▼
     2. [Wait Node] (Wait 15–30s; drops open TCP connection)
            │
            ▼
     3. [GET /v2/actor-runs/{runId}] (Fetch current status)
            │
            ▼
     4. [Switch Node: status]
            ├── "SUCCEEDED" ──────────► 5. [GET /v2/datasets/{defaultDatasetId}/items]
            │                                  │
            │                                  ▼
            │                          [Health Filter & Policy Gate]
            │
            ├── "RUNNING" / "READY" ──► (Loop back to Wait Node, max 20 retries)
            │
            └── "FAILED" / "TIMED-OUT"─► [Fail-Closed Alert] (Log error receipt, Art VII)
     ```
   - **Advantage:** Outbound-only HTTP traffic. Zero dropped sockets. No public ports or tunnels required.

## 2) n8n (T06 — decisions on the canvas)
1. Import `app/n8n/wf-m0-scan-decide.json` (n8n → Workflows → Import).
2. Credentials: HTTP Bearer = Apify token; Telegram node = bot token; Airtable = PAT (§4).
3. The POLICY Code node runs `app/n8n/policy_v0_node.js` (inline in the workflow). **Oracle parity rule (Art II.4):** node code must match `skin/policy.py::gate_v0` — run `python3 app/run_walking_skeleton.py --selftest` after any edit to either.
4. **Jev System 1 Decision & Safety Gateway Pattern (Spec'd P2 / Heuristic in M1):**
   - **M1 Runtime Implementation:** Deterministic pattern heuristics (`mm/jev.py` & `mm/inbound.py`) running locally without external network overhead or prompt injection leakage.
   - **P2 Spec Target:** Micro-model endpoint via OpenRouter / typesafe.ai or dedicated community node.
   - **Responsibilities:**
     - *Inbound Buyer Triage (`inbound.py`):* Deterministic routing into `dispute_t3`, `avail`, `offer`, `injection`.
     - *Hostile Screen (Art VI):* Closed-set safety screening over discrete buckets (`clean`, `injection_or_jailbreak`, `offplatform_payment`, `counterfeit`).
     - *2-Stage Comps Re-Ranking (Spec'd):* Re-ranks scraped sold comps to filter out noisy accessories and parts before computing `margin_z`.
   - **Parity Rule (Art II.4):** Gateway labels match the closed-set keys in `skin/buckets.json`.

## 3) Telegram (T08 — report + approvals)
1. BotFather → `/newbot` → `TELEGRAM_BOT_TOKEN`. Message the bot once. Get `TELEGRAM_CHAT_ID` via `https://api.telegram.org/bot<TOKEN>/getUpdates`.
2. Smoke: `--only report` sends one digest.

## 4) Airtable (receipts, Art VII)
1. PAT with `receipts` table. Columns: `receipt_id (text), ts (date), input_hash (text), action_state (single), reason_codes (text), policy_branch (text), tier (text), payload (long text), actor (text)`.
2. Or skip Airtable at M0: receipts land in `app/out/receipts.jsonl` (Art VII.1 degradation: rows acceptable, hash included).
3. **Google Sheets / Excel Triage Export:** Run `python3 app/run_walking_skeleton.py --export-csv` to output `app/out/triage_export.csv` containing `listing_id, price, health_score, margin_sigma, status, draft_text` — formatted for direct 1-click import into Google Sheets.

## 5) Browser-Use (T07 — acting)
- **M0 default = draft-assist** (no key needed): the offer is composed, written to `app/out/drafts/`, and pushed to Telegram with [approve] — human presses Send. `action_state: drafted → pursued_assisted` on confirm. (`drafted ≠ sent`, Art VII.2.)
- Optional live path later: `BROWSER_USE_KEY` + allowlist (send message · edit own price · bump own listing — nothing else, Art XII.1).

## 6) First live run (Friday 25 Sep evening — Run #1 hard gate by midnight)
```
python3 app/run_walking_skeleton.py --mode live            # full loop, 7 fixtures → real feed
python3 app/run_walking_skeleton.py --mode live --only scan --measure   # T05 cycle-time proof
python3 skin/policy.py --eval skin/gold.jsonl               # kill-switch metric still PASS
```
Then flip `wf-m0-scan-decide` schedule to the ~5-min cadence and arm `checklists.md` §3 (Run #1 hard gate: Friday 25 Sep midnight; Hero overnight Run #2: Sat 26 Sep 22:00).

## 7) Dual n8n Topologies: Portable Cron vs Enterprise Event-Driven

MarketMind ships with two distinct workflow topologies:

### Topology A: Portable Mode (Default — `wf-m0-scan-decide.json` & `wf-m1-full.json`)
- **Portability:** 100% universal. Runs out-of-the-box on vanilla n8n with zero plugins.
- **Trigger:** Cron schedule (`n8n-nodes-base.scheduleTrigger`) every ~5 minutes.
- **Apify Ingestion:** Standard `httpRequest` with Bearer token authentication in headers (never in URLs).
- **Use Case:** Rehearsals, video recording, judge evaluation, and instant one-click imports.

### Topology B: Enterprise Event-Driven Mode (`wf-m2-event-driven.json`)
- **Prerequisite:** Install the Apify community node in n8n:
  `Settings` → `Community Nodes` → `Install` → package: `@apify/n8n-nodes-apify`.
- **Trigger:** Webhook event via `Apify Trigger` (`ACTOR.RUN.SUCCEEDED`).
- **Latency Advantage:** Sub-second deal reaction. Eliminates the 5-minute polling window: as soon as the Apify crawler writes its dataset, n8n wakes up instantaneously.
- **Market Grounding:** Direct grounding against sold comps datasets, preventing hallucinations and ensuring closed-set valuation bounds.
- **Darko Integration:** Direct pipeline integration with the Deterministic Health Pre-Filter (`HEALTH_FLOOR = 25`), routing low-health items to skip receipts with zero LLM spend.

### Topology C: Async Polling Fallback (Mohammed Belfellah Pattern)
- **Architecture:** Outbound decoupled polling: `POST /runs` $\to$ `Wait (15s)` $\to$ `GET /actor-runs/{id}` polling loop $\to$ `GET /datasets/{id}/items`.
- **Use Case:** Production fallback when Apify runs exceed 60 seconds (deep pagination / bot challenge clearance) and public webhook ingress tunnels (ngrok/Cloudflare) cannot be established for Topology B.
- **Integrity Guarantee:** Prevents socket dropouts without introducing ghost listings; aborted crawls immediately trigger fail-closed error receipts.

## 8) MCP Scraper Suite: Reddit Intel & n8n Template Discovery

MarketMind configures two high-leverage Apify actors into its MCP environment (`app/mcp_config.json`):

1. **Reddit Intel (`labrat011/reddit-scraper`):**
   - On-demand qualitative defect trap cataloging (e.g. Canon AE-1 shutter squeak, Switch drift) and trending secondhand niche discovery.
   - CLI Tool: `python3 app/run_walking_skeleton.py --reddit-intel "<QUERY>"`.

2. **n8n Community Template Discovery (`datavoyantlab/n8n-templates-scraper`):**
   - Mines and inspects battle-tested n8n community workflow patterns directly from `n8n.io/workflows`.
   - Extracts complete, importable node graphs (`store_only_importable: true`) for rapid integration benchmarking.
   - Accessible to agents via the `n8n-template-scraper` MCP server.
