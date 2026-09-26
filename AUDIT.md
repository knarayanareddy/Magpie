# AUDIT — MarketMind engineering quality review (24 Sep 2026)

**Surfaces audited:** `marketmind/app/` (842 LOC Python/JS), `marketmind/skin/` (policy oracle), n8n workflows, CLI runner, Telegram digest, `env.example` + git hygiene, docs/tool consistency (README · WIRING · HUMAN-PLAYBOOK).
**Target user & tasks:** ① reseller at 07:00 reading the overnight digest (understand + control in <60s) · 2 operator at the Friday smoke (`--only scan` → numbers) · 3 judge at Q&A (verify claims live).
**Interface state:** CLI + Telegram text + n8n canvas — no web UI in scope (the four proof commands + digest are the product surface at demo time).

**Rubrics (grounding sources):**
- **impeccable** (pbakaus/impeccable) — `critique` (hierarchy/clarity), `harden` (edge cases, i18n, error states), `clarify` (UX copy), "AI-tell" scan, a11y baseline
- **21st/ui-review + design-sync** — single-source tokens, component/vocabulary coherence
- **ux-audit** (Thulr informed-skills + jezweb) — Nielsen's 10 heuristics, first-time-user lens, error recovery, WCAG/AT pass
- **security-audit** (claude-directory + agamm/claude-code-owasp) — OWASP Top 10:2025 + **Agentic AI ASI01–ASI10** (goal hijack, tool misuse, supply chain, rogue agents/kill switch, logging)

## Scorecard

| Pillar | Before | After fixes | Notes |
|---|---|---|---|
| Security (OWASP + Agentic) | **C+** | **A-** | 3 code-level vulns closed (C1/C2/C4); supply chain is a strength (stdlib-only) |
| Reliability & observability | B- | **A-** | append-only chained receipts, fail-closed feed errors, honest failure digest |
| UX / clarity (heuristics) | B | **A-** | promises match affordances; empty states; honest states everywhere |
| Tooling/docs consistency | **C** | **A** | `--measure`, `--only scan|report` now real (were documented-but-missing) |
| Privacy & ethics | A- | A- | ids/hashes-only receipts preserved; deliberate call on inbound text (below) |
| Testing | A | A | battery grew with the fixes (chain, env kill switch, URL spoof) |

## Findings by severity (fix status: ✅ applied & tested 24 Sep · 📋 deferred w/ rationale)

### P0 — would break the weekend or leak

| # | Finding | Rubric | Evidence | Fix |
|---|---|---|---|---|
| C1 | **Secret-leak path:** `.gitignore` entry `app/.env` is anchored to repo root and never matched the real `marketmind/app/.env` — a filled `.env` was committable | OWASP A02/A04 | `git check-ignore` pre-fix matched only the nonexistent root path | ✅ `**/app/.env`, `**/app/out/`; re-verified with `git check-ignore` |
| C2 | **Host-allowlist bypass (ASI02 Tool Misuse):** `_feed_url_ok` used `startswith("https://www.ebay.")` — `https://www.ebay.evil.com/…` passed; browser actuator could navigate attacker URLs | OWASP A01, ASI01/ASI02 | `browser_act.py` old prefix check | ✅ `urllib.parse` exact-host allowlist (10 hosts), https-only, no userinfo; selftest proves spoof blocked |
| C3 | **Tool/docs mismatch:** `--measure`, `--only scan`, `--only report` documented in WIRING/PLAYBOOK/M0-REPORT (5 sites) but absent from the CLI — Friday smoke row 1 would `unrecognized arguments` crash; `--only scan` printed nothing | ux-audit: error prevention; impeccable: harden | grep: docs vs `argparse` | ✅ `--measure` accepted (measurement always on); `--only scan` = read-only feed+cycle-time stage (no dedupe, no writes); `--only report` sends last digest via Telegram or prints it |

### P1 — trust, honesty, evidence integrity

| # | Finding | Rubric | Evidence | Fix |
|---|---|---|---|---|
| C4 | **Tokens in URLs + unredacted errors:** Apify token sent as `?token=` query (lands in tracebacks/proxies); `send_live` let Telegram's token-bearing URL escape in exceptions | OWASP A02/A09 "no secrets in URLs/logs" | old `notice.py`, `report.py`, n8n workflow URLs | ✅ Apify `Authorization: Bearer` (Python + n8n workflows); Telegram wrapped `RuntimeError(type name only)` |
| C5 | **Evidence destroyed per run:** `receipts.write` opened `"w"` — the overnight log (the 25% proof) would be overwritten by the next run; hash was input-only, not tamper-evident | OWASP A08/A09, ASI08 | old `receipts.py` | ✅ append-only + `prev_hash→row_hash` chain + `verify_chain()` (selftest + judge Q&A trump-card add-on) |
| C6 | **Unwired safety control:** `AUTO_PAUSE=1` documented in `env.example` as kill switch but read nowhere — trusting it was a false safety net | ASI10 Rogue Agents (kill switch must exist and work) | env.example vs config/runner | ✅ env checked at run start → observe-only; selftest proves it |
| C7 | **Failure = no log:** live-mode feed errors crashed with a raw traceback (possible URL/token leak) and produced no digest — Art VII.1 forbids "no log" | OWASP A10 fail-closed; ASI08 | old runner | ✅ `MMFeedError` (clean message), honest `SCAN FAILED` digest, exit 2 |
| C3h | **Affordances that don't exist:** digest showed `[approve] [override→escalate]` buttons with no wired handlers ("unwired buzzwords" kiss-of-death) | ux-audit: system status honesty | old `report.py` | ✅ line shows only live controls (`/pause`, human-Send drafts); buttons return with T20 handlers (staged like gate v1) |

### P2 — polish, coherence (impeccable polish/clarify + 21st tokens)

| # | Finding | Rubric | Fix |
|---|---|---|---|
| C8 | Digest cap counter showed per-run drafts, not the nightly total (state tracked it correctly) | Nielsen 1 consistency | ✅ `outreach_used` from state |
| C9 | `browser_act.ALLOWLIST` duplicated `config.ACTION_ALLOWLIST` (two token sources) | 21st design-sync: single source | ✅ imports from config |
| C10 | Draft signature rendered `— unset` to sellers when consent unfilled (AI-tell, embarrassing live) | impeccable: AI-tells; Art III.3 chrome-only | ✅ signature omitted until `NAMED_RESELLER` set |
| C11 | Empty states: "refused first:" with zero rows; zero-scanned feed gave no guidance | ux-audit: empty states | ✅ "(none this run)", "empty feed — check APIFY_ACTOR_LISTINGS / quota" |
| R3 | Live actor prices like `"€150"` crashed `float()` | impeccable: harden | ✅ `_safe_float` in `notice.py` |

## Deliberate non-findings (defensible, documented)
- **A11y/AT pass: N/A by design** — surfaces are CLI and Telegram plain text (screen-reader linear, no contrast/focus issues); noted per WCAG-pass requirement that this is surface-limited.
- **Inbound message text stored verbatim** in `inbound-outcomes.json` — Art III.4 restricts *receipts* to ids/hashes; demo data is user's own accounts' messages (Art III). Flagged if third-party text is ever ingested.
- **Reason codes stay snake_case in the digest** (`price_too_good`, `dispute_t3`) — ux-audit's "plain language" rule is overridden deliberately: codes are the receipts that make the Q&A verifiable; glossary lives in `skin/gold.jsonl`.
- **UTC day-rollover for the 5/night cap** (resets 02:00 NL) — conservative, unchanged before the event.
- **VL image URLs are handed to the model provider** (provider fetches, not us) — raise-only use, text-only degrade documented (Art VI); pre-filtering image hosts is post-event.
- **Python 3.10+ stdlib only** — supply-chain risk ≈ 0 (OWASP A03); pinning applies to the Apify actor id (`env.example`) and n8n nodes (parity-tested mirrors).

## Residual risks (weekend watch-list)
1. **`--only report` sends the last rendered digest** — fine for smoke; if the night run fails, the failure digest is what gets sent (honest).
2. **Judge prompt injection via model provider output** — mitigated by coercion helpers (invented labels → `unknown` → escalate); raise-only rule is the backstop.
3. **Apify actor output shape drift** — `_normalize` tolerates missing keys (defaults), but a radically different actor still needs the WIRING §1 schema check on Friday.

## Verification run (post-fix battery, Sat 26 Sep 2026 Round 2)
```
gold eval:        rows=9 mismatches=0 hostile→pursue=0   PASS
selftest:         run1 {skip 2, esc 3, drafted 1, auto 1} · dedupe 7 · pause ok · AUTO_PAUSE ok · chain ok · URL spoof blocked · confirm forgery blocked · paused confirm blocked · watchlist cycle-2 resolved · sim cost honest   PASS
M1+M2-stage:      PASS
parity v0+v1:     33/33 (standalone files + all 3 inline workflows)   PASS
gitignore:        marketmind/app/.env + out/ → ignored   verified
scan stage:       7 items + cycle time printed   verified
fail-closed:      live w/o keys → SCAN FAILED digest, exit 2   verified
```

### Round 2 Hardening (Sat 26 Sep 2026):
- **C12 (Art III / Constitutional Anti-Profiling):** `health.py` and `wf-m2` stripped of all seller account age/rating signals. Gated purely on listing content (title, desc, photos, price validity, freshness). `HEALTH_FLOOR = 25`. Skips labeled `prefilter:health`.
- **C13 (Art IV.3 / Cost Honesty):** `costs.py` and runner only track Apify/LLM expenses when `mode == "live"`. Sim runs print `cost: unmeasured (sim run)`.
- **C14 (Art VII.2 / Forgery Prevention):** `confirm()` now strictly requires an existing receipt with `action_state == "drafted"`. Refuses unknown listings, hostile listings, and paused kill-switch state.
- **C15 (Art XIII / Design Lockfile):** `triage.html` overhauled to Paper `#F3EFE7` + Ink `#1C1915` + Rule `#C9C2B4`, border-radius 2px, no emoji icons. Buttons labeled honestly (`Mark Reviewed in Browser`), directing to CLI `--confirm`. Proper HTML/CSS attribute escaping prevents injection.
- **C16 (Watchlist Liveness):** Watchlist revisit loop allows items with newly arrived comps to bypass `is_seen()`, re-evaluating them through the decision pipeline and resolving.
- **C17 (Canvas Receipt Completeness):** Switch nodes in `wf-m0`, `wf-m1`, and `wf-m2` route `skipped` decisions directly to Airtable receipt generation (100% receipt coverage, US-7).
- **C18 (Prompt Parity & Voice):** Judge prompt parity aligned with 3 protections; Dutch reseller outreach voice unified across Python and all 3 workflows with non-coercive opt-out clause.
- **C19 (MCP Pinning):** `@apify/actors-mcp-server` pinned to `@0.16.0` in `mcp_config.json`.
