# MarketMind — Tasks (Supercharged Edition)

Execute **in milestone order**. Article I: M0–M1 are veto-prioritized over M2+. Done-done = AC passes + test green + receipt/log exists. Gate column shows which gate version is legal at that point.

---

## Phase 0 — Decisions & law (Completed)
- [x] **T01** Sitting-1 panel verdicts ratified (`../01`): Trust Ladder, measured latency, learning ledger, fallbacks, scam-bait inversion.
- [x] **T02** Sitting-2 ListGuard discipline adopted (`../02`): closed sets, policy-in-code, injection intercept, receipts, gold fixtures, untrusted asymmetry.
- [x] **T03** Mentor feedback ratified as Constitution **Article I** (core loop first; gate second).

## Phase 1 — M0 · Walking skeleton (~3h) — gate **v0**
Goal: **one real listing, one real decision, one real action, one real report. Ugly is fine.**
- [ ] **T04** Kickoff prep (concrete dates): demo + 2 counterparty accounts **Thu 24** (warm Thu–Fri with light normal use) · consent + `NAMED_RESELLER` + H1/H2 freeze **Thu 24** · 5 own listings posted **Fri 26** · keys probed **Fri 26** (incl. TF → record `live|fallback`) · **live smoke run Fri evening** (one scan → one decision → one draft → one digest; label "dress rehearsal").
- [ ] **T05** Apify actor up with one **real** run; dataset shape captured in `plan.md` terms; run cycle time **measured** (kills the 60s myth).
- [ ] **T06** n8n: `wf-scan` → `wf-decide` minimal (comps lookup for one item + `margin_z` + **gate v0 only**).
- [ ] **T07** One action path proven end-to-end (T1 reprice on own listing OR T2 offer to pre-arranged counterparty; draft-assist acceptable).
- [ ] **T08** One Telegram report line sent (counts can be hardcoded format; content real). **M0 DONE when a stranger could watch this run and call it "a thing that acts."**

## Phase 2 — M1 · Core loop closes (~5h) — gate **v0**
Goal: the product works **unattended**. Overnight-capable.
- [ ] **T09** Scan cadence + `seen-ids` + pHash dedupe (re-posts don't double-offer).
- [ ] **T10** Comps pipeline solid (eBay sold median/MAD) + `margin_z`; `no_comps ⇒ escalate` fail-closed.
- [ ] **T11** Trust tier v1 per `plan.md` §4 + `MAX_COLD_OUTREACH` enforced in code + `/pause` `/resume` kill switch live. Wire T2/T3 approvals via **n8n native human-in-the-loop tool-approval** where available; Telegram approve buttons as fallback + digest surface.
- [ ] **T12** ListingPilot minimal: stale-rule (no views N days) → reprice/bump own listing; inbound reply with dispute-words → T3 escalate.
- [ ] **T13** Browser-Use act path + **one witnessed draft-assist fallback** (the ladder is real, not slides).
- [ ] **T14** Digest v1: scanned · skipped · escalated · acted (by `action_state`) · learned (`unmeasured` OK) + named human + risk-tier footer.
- [ ] **T15** **Hero overnight run — Sat 26 Sep 22:00 → Sun 27 Sep** (hero run #2 with full capture per `checklists.md` §3; run #1 was Fri 25 Sep hard gate). Measure first-touch p50 → replaces `unmeasured`. **Hard gate (judge mandate, sitting 3): the run must be armed before Sat midnight — no logged run ⇒ no proof for the 15:00 video.**

### ⛔ GATE CHECKPOINT — Core-First Warden sign-off required before any Phase 3 task
M1 done-done = T09–T15 green. The Warden vetoes gate commits until then. (Art I.3)

## Phase 3 — M2 · Gate v1 (~5h) — only after checkpoint
- [ ] **T16** `skin/` live: `buckets.json` + `questions.json` wired to `MODEL_JUDGE`; `policy.py` mirrored in n8n `POLICY` node; oracle test `python skin/policy.py --eval skin/gold.jsonl` green.
- [ ] **T17** Injection intercept wired at both input surfaces (listing text, buyer messages); `mm-inject-01` one-click repro.
- [ ] **T18** Receipts v1: UUID + `input_hash` + reason codes + `actor=human` on override; digest counts receipts.
- [ ] **T19** Degradations honest: `judge=unconfigured`, `grounding=stale`, `drafted` states verified by hand once each.

## Phase 4 — M3 · Proof & learning (~4h)
- [ ] **T20** Gold eval run + 3-column table (Art IV; `n/a` legal) + kill-switch metric shown: **hostile→pursue = 0**.
- [ ] **T21** Learning ledger: priors before/after run #2 vs H1/H2 (or `unmeasured` with cause).
- [ ] **T22** **Overnight run #2 — hero run** (full tiers within caps). Capture everything.
- [ ] **T23** Claims audit pass against `../01` §3 table + `checklists.md` §6. No unmeasured number shipped as fact.

## Phase 5 — Ship
- [ ] **T24** Video (2 min, `spec.md` §4 beats, hostile-first among decisions) + fallback recordings **before Sun noon**.
- [ ] **T25** Submission + Q&A drill (`checklists.md` §6–7). Freeze Sun 15:00.

## Phase 6 — M4 · Enhancements & Stretch (P2 — never at loop expense)
- [ ] **T26** TF two-knob + €-cost per receipt (Art II.3 / IV.2 `€/listing` column).
- [ ] **T27** pHash → prior-verdict cache (JEV-style 0-token hits on re-posts).
- [ ] **T28** Receipt-pack export (Exhibit-style `exhibit.json`) for Q&A appendix.
- [ ] **T29** Gold padding toward n≥40 (Art IV floor is n≥8).
- [ ] **T30** Full three-column benchmark incl. p50 latency row.
- [x] **T31** Deterministic Content Health Pre-Filter (`HEALTH_FLOOR = 25`, Art III content-only, zero seller profiling).
- [x] **T32** Visual Triage Grid (`triage.html` adhering to Art XIII lockfile + honest CLI `--confirm` integration).
- [x] **T33** Google Sheets CSV Exporter (`--export-csv` $\to$ `triage_export.csv`).
- [x] **T34** Watchlist Revisit Loop (resolves pending items in pipeline when market comps arrive).
- [x] **T35** Event-Driven Topology (`wf-m2-event-driven.json` webhook trigger + async polling fallback pattern).
- [x] **T36** Apify MCP Scraper Suite (`labrat011/reddit-scraper` defect lookup + `datavoyantlab/n8n-templates-scraper`).

---

## Definition of done-done (all phases)
1. Acceptance criteria in `spec.md` pass and are testable without the video.
2. Tests green: `python skin/policy.py --eval skin/gold.jsonl` (after T16) + security spot-checks (`threat-model.md` §4).
3. A receipt or log line exists for every decision. `drafted ≠ sent`.
4. Killed-list check (`ORIGIN.md` §4): the change does not revive anything on it.
