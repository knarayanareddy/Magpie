# Magpie — Build Weekend (Prosus) · 25–27 Sep 2026

> An autonomous classifieds agent scout that swoops on underpriced classifieds, haggles, spots margin, and closes secondhand deals while you sleep. "We judge listings, not people."

## Quickstart — the proofs (all must be green)
```bash
python3 marketmind/skin/policy.py --eval marketmind/skin/gold.jsonl   # kill-switch: hostile->pursue = 0
python3 marketmind/app/run_walking_skeleton.py --selftest             # loop + seen-ids + pause + caps
python3 marketmind/app/tests/test_m1.py                               # M1 behaviors
python3 marketmind/app/tests/test_gate_parity.py                      # python oracle == n8n JS node
```

## Map
| Path | What |
|---|---|
| `marketmind/README.md` | **Start here** — spec package reading order |
| `marketmind/constitution.md` | 13 articles (Art I = mentor's core-first rule) |
| `marketmind/{spec,plan,tasks,BUILD,checklists,threat-model,design,WIRING,M0-REPORT}.md` | SDD package (ListGuard lineage) |
| `marketmind/skin/` | gate oracle (`policy.py`), closed sets, `gold.jsonl` |
| `marketmind/app/` | runtime: `mm/` (notice→decide→act→report), `n8n/` (importable workflow + JS policy mirror), `fixtures/` |
| `marketmind/kickoff/` | consent, preregistration (H1/H2), listing plan |
| `01…04-*.md` | the four review sittings (expert panel → ListGuard integration → tech stack → judge pre-mortem) |

## On the day (kickoff Sat 26 Sep)
1. Walk in with the tested loop + `wf-m0-scan-decide.json` (import to n8n) — wire live keys per `marketmind/WIRING.md`.
2. **Hero overnight: Sat 26 Sep 22:00 → Sun** — the "while you weren't watching" proof. `checklists.md` §3 (Run #2).
3. Video Sun 27 Sep 15:00 — 5 beats: **log → refusal → action → assisted → close** (`spec.md` §4). Q&A trump card: run the gold eval live.

## Your turn (code can't do these)
**→ `HUMAN-PLAYBOOK.md` is the step-by-step runbook (Thu 24 → Sun 27 Sep: accounts · consent · listings · credits · live smoke · hero overnight · film · submit)** — every step timed, with done-criteria and fallbacks.
