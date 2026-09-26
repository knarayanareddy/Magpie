# M0 — Walking Skeleton: Report Card
**Status: ✅ SKELETON RUNS (sim-proven tonight) · live swap = keys + human punch list (`WIRING.md`, 30–60 min)**
Loop proven end-to-end: **NOTICE → DECIDE → ACT → REPORT** with receipts, a real Dutch offer draft, and the honest digest. Gate **v0** only — per judge mandate and the mentor's core-first rule. The gate did not get to eat the weekend; it's three rules in one file.

---

## 1. Definition of done — T04–T08

| Task | Status | Where |
|---|---|---|
| **T04** Thu kickoff | 🟡 **human punch list ready** | `kickoff/consent.txt` (sign!) · `kickoff/PREREGISTRATION.md` (H1/H2 frozen) · `kickoff/LISTING-PLAN.md` (5 items) · `app/env.example` (keys) |
| **T05** Apify + one real run + cycle measured | 🟡 **code ready, sim-measured; live pending `APFY_TOKEN`** | `mm/notice.py` (live client + `_normalize` schema map) · WIRING §1 smoke: `--mode live --only scan --measure` |
| **T06** n8n wf-scan→wf-decide (comps + margin_z + gate v0) | ✅ **built + parity-tested** | `app/n8n/wf-m0-scan-decide.json` (importable) · `app/n8n/policy_v0_node.js` ↔ `skin/policy.py` **parity PASS (6/6)** |
| **T07** One action path end-to-end (draft-assist OK) | ✅ **proven in sim** | `mm/act.py` — offer €110 (79% of ask, H1 band), NL+EN templates, 2-round cap, allowlist; T1 reprice path also exercised |
| **T08** One Telegram report line | ✅ **digest rendered (design.md format); live send wired** | `app/out/digest.txt` · `mm/report.send_live()` awaiting `TELEGRAM_*` |

**M0 done-done definition** ("a stranger watching would say *it acts*") — **met in sim**; flip to live with WIRING §6.

## 2. Evidence (all runs today, `marketmind/app/out/`)

```
1. GOLD EVAL        rows=9  mismatches=0  hostile->pursue=0   BUILD-BREAKING METRIC: PASS
2. SELFTEST         PASS  {skipped:2, escalated:3, drafted:1, pursued_auto:1}
3. GATE PARITY      PASS  6/6 (python oracle == n8n Code-node mirror)
4. SIM RUN          m0-sim-v0 — full loop, receipts.jsonl + digest.txt + drafts/
```

Digest (abridged — full in `app/out/digest.txt`):
```
MarketMind — while you slept (for unset)  [m0-sim-v0]
scanned 7 · skipped 2 · escalated 3 · acted 2 (auto 1 / drafted 1 awaiting you)
refused first:
  ESC  mm-live-iphone-01      price_too_good
  SKIP mm-live-inject-01      injection_or_jailbreak
  ESC  mm-live-bike-01        price_too_good
acted:
  DRAFT  mm-live-switch-01    offer €110 (79% of ask, round 1/3)
cold-outreach cap: 1/5 used tonight · first-touch: (sim label) · money moved: €0
```
Draft (real message, awaiting human Send — `drafted ≠ sent`, Art VII.2):
> *"Hoi! Ik zag je Nintendo Switch V2 met doos te koop staan. Zou je €110 willen accepteren? … — unset"*

Receipts: 7 rows, each with UUID + SHA-256 input hash + `policy_branch: gate_v0:*` + reason codes (`app/out/receipts.jsonl`). `for unset` is **correct**: consent unsigned ⇒ `NAMED_RESELLER=unset` shown (Art III.3). It changes the moment `consent.txt` is signed.

## 3. Honesty labels (Art IV.3)
- All timings above are **local pipeline wall time**, labeled as such — the marketplace first-touch p50 stays `unmeasured` until T15's live run. Nothing invented.
- Sim dataset is `app/fixtures/` (7 realistic listings incl. 4 hostile). Live feed replaces it unchanged (`--mode live`).

## 4. Two spec clarifications made under build pressure (logged per Art X)
1. **Gate v0 rule 1 = hostile-text screen** (deterministic): now covers injection phrases + advance-fee/IBAN patterns alongside illegal keywords — required so run #1 cannot act on `mm-inject-01`-style bait before gate v1 exists (Art VI: hostile in-scope from day one). Still 3 rules, zero models.
2. **`drafted` is a first-class pre-state** of `action_state` (`drafted → pursued_assisted` on human confirm) — the concrete form of "drafted ≠ sent" (Art VII.2).

## 5. What M0 deliberately did NOT build (warden log)
No buckets/judge model (M2) · no receipts-in-Airtable (rows + hash suffice, Art VII.1) · no JEV/TF/MLX (unwired tech stays unnamed) · no Browser-Use (draft-assist is the M0 action path) · no seen-ids/digest aggregation polish (M1 T09/T14). The gate stayed at three rules. **Total build time: one sitting.**

## 6. Punch list before the hero overnight (Sat 26 Sep 22:00 — dates pinned in `plan.md`)
1. Human: sign `consent.txt` → set `NAMED_RESELLER` · create demo + 2 counterparty accounts · post 5 listings · freeze preregistration. (`WIRING.md` §0)
2. Keys: Apify token + listing actor id (WIRING §1) → run `--mode live --only scan --measure` and **write the measured cycle time into the digest** (T05).
3. Telegram bot (WIRING §3) → `--only report` smoke.
4. Import `wf-m0-scan-decide.json`, wire credentials, flip schedule (~5 min cadence) (WIRING §2).
5. Re-run the three tests (gold eval, selftest, parity) after any edit — `checklists.md` §2 milestone gates.
6. 22:00 Sat 26 Sep: arm hero overnight run #2 per `checklists.md` §3. **Friday 25 Sep midnight is the hard gate for Run #1** (`plan.md` §6, `04-judge` mandate 2): no run #1 logged ⇒ Sunday has no proof.

Then M1: T09–T15 (seen-ids, comps pipeline live, trust tier + `/pause`, ListingPilot minimal, digest v1).
