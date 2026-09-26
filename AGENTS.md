# AGENTS.md: Operational Directives for Magpie Autonomous Agent

> **Audience:** Autonomous Coding Agents (Hermes CLI, Opus 5.5, GLM 5.3, Antigravity).  
> **Mission:** Build, test, refine, and operate **Magpie**—the autonomous classifieds arbitrage agent for the Prosus Build Weekend (25–27 Sep 2026).  
> **Repository:** `https://github.com/knarayanareddy/Magpie`  
> **Core Rule:** "Build something that acts on its own. We judge listings, not people."

---

## 1. Dual-Engine Model Architecture

- **Primary Reasoning Model (Claude Opus 5.5):**
  - Handles architectural decisions, prompt engineering, adversarial threat modeling, constitutional conformance, and high-level reasoning.
- **Execution Model (GLM 5.3 Flash via Nebius TokenFactory):**
  - Handles fast deterministic tool execution, file edits, test battery execution, git synchronization, and live marketplace feed polling.

---

## 2. Prime Directives (Non-Negotiable Constitution)

1. **Axiom 1: Models Propose, Deterministic Code Decides (Article V)**
   - Foundation models never directly call external mutation tools (no direct purchases, no binding bids, no irreversible marketplace mutations).
   - Models return typed, closed-set JSON answers (e.g. `policy_bucket`, `counterfeit_risk`, `injection_or_jailbreak`).
   - Pure deterministic code in `marketmind/skin/policy.py` (and its mirrored n8n Code nodes) evaluates the facts and decides `pursue`, `escalate`, or `skip`.

2. **Axiom 2: Fail-Closed by Law (Article V.2)**
   - Missing or ambiguous data always routes to `escalate` or `skip`, never to `pursue`.
   - Missing comps (`mz is None`) $\rightarrow$ `escalate` with reason `no_comps`.
   - Hostile text, prompt injection, or illegal keywords $\rightarrow$ `skip` immediately. Build-breaking metric: `hostile -> pursue must be 0`.

3. **Axiom 3: Zero Seller Profiling (Article III & US-1b)**
   - Evaluates **listing content only** (photos, description, price-to-comps ratio, freshness).
   - ZERO seller-derived attributes: no account age, no rating count, no profiling of human beings.

4. **Axiom 4: Cryptographic, Immutable Receipts (Article VII)**
   - Every single decision emits an append-only receipt into `marketmind/app/out/receipts.jsonl`.
   - Each receipt contains SHA-256 hash chains (`input_hash`, `prev_hash`).
   - Human actions (e.g. clicking Send via `--confirm`) emit `action_state = "pursued_assisted"` with `actor = "human"`.

5. **Axiom 5: Parity Between Python Oracle and n8n Workflows (Article II.4)**
   - Any modification to `marketmind/skin/policy.py` must be mirrored in:
     - `marketmind/app/n8n/policy_v0_node.js` & `policy_v1_node.js`
     - Inline code nodes in `wf-m0-scan-decide.json`, `wf-m1-full.json`, and `wf-m2-event-driven.json`
   - Parity test (`marketmind/app/tests/test_gate_parity.py`) must pass 100%.

---

## 3. Directory Map & Key Files

| Path | Purpose |
|---|---|
| `marketmind/skin/policy.py` | Gate Oracle: `gate_v0` (heuristic 3-rule screen) and `gate_v1` (content-judged screen) |
| `marketmind/skin/gold.jsonl` | Gold evaluation dataset for the build-breaking safety metric |
| `marketmind/app/run_walking_skeleton.py` | Main loop CLI: `NOTICE -> DECIDE -> ACT -> REPORT` (supports `--selftest`, `--confirm`, `--outcome`, `--mode live`) |
| `marketmind/app/mm/` | Domain logic: `notice.py`, `decide.py`, `act.py`, `receipts.py`, `health.py`, `inbound.py`, `jev.py`, `costs.py`, `triage.py`, `watchlist.py` |
| `marketmind/app/n8n/` | Ready-to-import n8n workflows (`wf-m0`, `wf-m1`, `wf-m2`) and JS policy mirrors |
| `marketmind/app/fixtures/` | Offline sample datasets (`apify_sample_dataset.json`, `comps_sample.json`, `low_health_listing.json`) |
| `marketmind/kickoff/` | Hackathon consent forms, H1/H2 pre-registration, and initial listing plan |
| `HUMAN-PLAYBOOK.md` | The hour-by-hour operational runbook for the hackathon weekend |

---

## 4. Verification Battery (Must Run Before Any Push)

Whenever code changes are made, run all 4 proofs to confirm PASS:

```bash
# 1. Gold safety eval (hostile->pursue must equal 0)
python3 marketmind/skin/policy.py --eval marketmind/skin/gold.jsonl

# 2. Self-test (hash-chain integrity, kill-switch, dedupes, comps revisit)
python3 marketmind/app/run_walking_skeleton.py --selftest

# 3. M1 behavior tests
python3 marketmind/app/tests/test_m1.py

# 4. Gate & health parity test (Python vs standalone JS vs 3 inline n8n workflows)
python3 marketmind/app/tests/test_gate_parity.py

# 5-9. Hardening, n8n Code nodes (in Node), sell co-pilot (US-9), market memory (US-10) + its loop wiring
python3 marketmind/app/tests/test_hardening.py
python3 marketmind/app/tests/test_n8n_nodes.py
python3 marketmind/app/tests/test_sell.py
python3 marketmind/app/tests/test_memory.py
python3 marketmind/app/tests/test_memory_loop.py
```

**Market memory kill switches (US-10, live mode only, fail-open):** `MEM_ALL=0` = exact legacy behaviour; per feature `MEM_INGEST` / `MEM_COMPS` / `MEM_VERDICT` / `MEM_CADENCE` `=0`. Store: `marketmind/app/out/market.db` (gitignored). Sync sidecar: `marketmind/app/bin/memory-sync.sh start|stop|status`. Metrics: `python3 marketmind/app/tools/memory_metrics.py`.

---

## 5. Hackathon Event Day Deliverables & Schedule

- **Saturday 22:00:** Hero overnight run (#2) begins. System operates autonomously while team sleeps.
- **Sunday 15:00:** 3-minute video due showing the 5 beats:
  1. **Log:** Live feed ingestion & deterministic deduplication.
  2. **Refusal:** Hostile scam/jailbreak flagged and safely skipped with audit receipt.
  3. **Action:** Genuine margin opportunity noticed, grounded comps calculated, Dutch offer drafted.
  4. **Assisted:** Human review via Telegram / CLI `--confirm`, signed receipt emitted.
  5. **Close:** H1/H2 learning ledger updated, unit economics cost line reported.

---

## 14. Reference Resources

Use these for context when building n8n workflows, Apify integrations, and the orchestration layer:

- **n8n MCP server:** https://github.com/czlonkowski/n8n-mcp — MCP for building n8n workflows programmatically
- **n8n Skills:** https://github.com/czlonkowski/n8n-skills — skillset for building flawless n8n workflows
- **Apify n8n Nodes:** https://github.com/apify/n8n-nodes-apify — official Apify nodes for n8n
- **Thread:** https://x.com/tomcrawshaw01/status/2011804665147449652
- **Ref:** https://t.co/bY1c8D4amz
- **Ref:** https://t.co/0LqslJzct6

**Focus:** European classifieds (Marktplaats NL). Comps should target eBay.nl / EU markets, not eBay.com USD.

---

## 15. Autonomous Hero Loop & Operational Directives

### Architecture & Grounding
- **Classifieds Feed:** `haketa/marktplaats-scraper` focused on Benelux tech (`MP_TECH_QUERIES=nintendo switch,ps5,iphone 14,macbook`).
- **European Comps Grounding:** `automation-lab/ebay-scraper` targeting `EBAY_MARKETPLACE=DE` (Germany / EU continental) natively in EUR (€). Accessory filters in `mm/rerank.py` strip non-device items (skins, fans, cables, empty boxes).
- **Comps Cache:** Saved to `marketmind/app/out/comps_cache.json` with 2-hour TTL (`COMPS_CACHE_TTL_S=7200`) so recurring autonomous cycles do not incur redundant comp scraping spend.

### Autonomous Continuous Execution
Run the live pipeline continuously:
```bash
# Run continuous autonomous loop (default: every 300s / 5 mins)
python3 marketmind/app/run_walking_skeleton.py --mode live --loop --interval 300

# Run in background as persistent daemon:
nohup python3 marketmind/app/run_walking_skeleton.py --mode live --loop --interval 300 > marketmind/app/out/daemon.log 2>&1 &
```

### Safety & Kill-Switch
- **Pause immediately:** `python3 marketmind/app/run_walking_skeleton.py --pause` or set `AUTO_PAUSE=1` in `app/.env`
- **Resume operation:** `python3 marketmind/app/run_walking_skeleton.py --resume` or set `AUTO_PAUSE=0`
- **Health monitoring:** Check `marketmind/app/out/daemon_health.json` and `marketmind/app/out/run-summary.json`

### Review & Human In The Loop
- **Triage Grid:** Open `marketmind/app/out/triage.html` in browser
- **Google Sheets:** Import `marketmind/app/out/triage_export.csv`
- **Confirm Draft:** `python3 marketmind/app/run_walking_skeleton.py --confirm <DRAFT_ID>`

