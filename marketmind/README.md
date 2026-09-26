# MarketMind — Spec Package (Build Weekend, Prosus)

> Autonomous classifieds buy+sell operator. Skin id: `marketmind`. Workers: FlipScout (buy) + ListingPilot (sell).
> Built in the SDD discipline of `knarayanareddy/4prd` (ListGuard lineage): spec wins over code, closed sets, fail-closed policy, gold fixtures, receipts.

**Event:** Build Weekend — "what you build has to act autonomously." · **Rule of the house:** Apify pulls the real-world data, n8n runs the workflows and the decisions.

---

## Reading order (do not skip)

1. `ORIGIN.md` — why this exists, what the panels killed, **the mentor feedback (Art I)**
2. `constitution.md` — 13 ratified articles. Agents must not weaken them.
3. `spec.md` — what we are building (Supercharged Edition)
4. `plan.md` — how it is assembled (architecture, stack, cuts)
5. `tasks.md` — T-numbers, milestones M0–M4, check-boxes
6. `BUILD.md` — council seats & vetos, build order, stop-the-lines, non-negotiables
7. `threat-model.md` + `design.md` — containment and visual/format lockfiles
8. `checklists.md` — kickoff / overnight / demo-day / submission / Q&A
9. `skin/` — `buckets.json`, `questions.json`, `policy.py`, `gold.jsonl`

Context docs (already written): `../01-expert-panel-review.md`, `../02-listguard-integration-assessment.md`.

---

## Milestone legend (Article I enforces this order)

| Milestone | Name | Status | Gate |
|---|---|---|---|
| **M0** | Walking skeleton — one listing, one decision, one action, one report | ✅ green (selftest pass) | gate v0 (3 rules) |
| **M1** | Core loop closes unattended (overnight-capable) | in progress | gate v0 |
| **M2** | Gate v1 — closed sets, injection intercept, receipts | vetoed until M1 done | gate v1 |
| **M3** | Proof — gold eval, learning ledger, hero run | not started | gate v1 |
| **M4** | Stretch — TF economics, pHash cache, exhibit pack | not started | gate v1 |

**"Done-done" means:** acceptance criteria in `tasks.md` pass, a test is green, and a receipt or log line exists. Not "demoable in a video."

## Quickstart & Proof Commands

**Prerequisites:** Python >= 3.10, Node.js >= 18 (required for JS policy node parity validation).

```bash
# 1. Run local walking skeleton (sim mode, deterministic)
python3 app/run_walking_skeleton.py

# 2. Run full self-test verification battery
python3 app/run_walking_skeleton.py --selftest

# 3. Human confirm a drafted offer -> emit pursued_assisted signed receipt (Art VII.2)
python3 app/run_walking_skeleton.py --confirm mm-live-switch-01

# 4. Record offer outcome into H1 learning ledger (T20/US-8)
python3 app/run_walking_skeleton.py --outcome offer-switch-01 accepted

# 5. Export triage table to CSV for Google Sheets
python3 app/run_walking_skeleton.py --export-csv

# 6. Verify 33-point gate parity across Python oracle, JS mirrors, and 3 inline workflows
python3 app/tests/test_gate_parity.py

# 7. Evaluate gold set (hostile->pursue = 0 build-breaking metric)
python3 skin/policy.py --eval skin/gold.jsonl
```

---

## Article X reminder

These markdown files **are** the spec. Acceptance criteria are testable without a pitch deck. Changing behaviour requires changing the spec first. A `plan.md` may *narrow* scope; it may not relax the constitution.
