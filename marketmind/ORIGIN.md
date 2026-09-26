# MarketMind — how this idea was conceived, and what it survived

**This file is memory: why this product exists. Do not reopen killed ideas. Do not build GhostChef. Do not ship a second product.**

---

## 1. Conception

Resellers on Marktplaats/eBay/Vinted run two full-time jobs: hunting underpriced deals before competitors (seconds matter) and babysitting their own listings (repricing, bumping, answering buyers). They do 3–5 h/day and still miss deals and let listings go stale. The Build Weekend brief quotes this world verbatim: *"Price inventory directly from photos. Negotiate and close a sale without the seller typing a word."*

**Job To Be Done:** operate my resale desk while I sleep — notice new listings and my stale ones, decide with real comps, act within earned limits, and hand me an honest morning report.

**Merged from:** FlipScout (buy) + ListingPilot (sell) — one supervisor, two n8n worker workflows, one trust ladder.

---

## 2. What the panels did to it (sittings 1–2, `../01`, `../02`)

| Sitting | What it did |
|---|---|
| **Sitting 1 — 5-expert panel** | MarketMind 4–1 over GhostChef. Killed: payment links, unbounded auto-negotiation, "60s scan" fiction, RL talk, the iPhone/bike **hero** beats (scam bait — they became refusal beats). Imposed: Trust Ladder T0–T3, measured latency, learning ledger with pre-registered hypotheses, pre-registered fallback ladder, niche demo category (consoles/camera gear). |
| **Sitting 2 — ListGuard integration** | Adopted the decision discipline: closed buckets, Noul/Choice typed questions, fail-closed policy table ("models propose, code decides"), injection intercept, receipts (`actor=human`), gold fixtures with **hostile→pursue = 0**, untrusted-input asymmetry (grounding may raise suspicion, never lower it), "rationale cannot change action." Score 9.1 → 9.4. |
| **Sitting 2 kills** | Seller reputation scores / person DB (constitutional), third-party reporting or takedowns, whole-harness-as-decision-engine (n8n owns decisions), fear-pitch ("fines tomorrow"), ListGuard branding / OLX logo-jacking. |

---

## 3. The mentor intervention — 24 Sep 2026 (ratified as Constitution Article I)

> **"Don't let the gate consume all your build time. A beautiful safety system on a non-functional product scores zero. Core functionality first, gate second."**

What changed because of it:

1. **Milestones re-cut around a walking skeleton.** M0 (one listing end-to-end, ugly) and M1 (loop closes unattended) are built **before any gate v1 work exists on any branch**. The gate ships as v0 — three rules — sufficient to act in the real world.
2. **A Core-First Warden seat** with a hard veto: no gate commit before M1 is done-done (`BUILD.md`).
3. **Stop-the-lines** in `plan.md` §6 convert the advice into dated cut rules (ship v0 gate on Sat 18:00 if v1 is not green).
4. Sitting 2's M2 gate features keep their design but **lose their priority**. Receipts may degrade to plain log rows; the eval table may degrade to the overnight receipt count. The loop may not degrade to nothing.

The gate is still real — 12 lines of policy and closed sets from `skin/`. It is second, not deleted.

---

## 4. Killed on this path (do not revive)

- Payment links / any money movement (agent's mandate ends at the handshake: "deal agreed, pickup via platform flow")
- Unbounded auto-negotiation (max 2 counter-rounds, price ceiling, trust-budget per round)
- Seller reputation scores, person databases, cross-listing profiles of humans ("we judge listings, not people")
- Reporting sellers, requesting takedowns, moderating third parties (self-directed actions only)
- Scam-bait demo beats as "opportunities" (iPhone 62%-margin and €800-bike-for-€400 are **refusal** material)
- "Scans every 60s" claims; unmeasured latency numbers; invented metrics (`unmeasured` is legal, invented is not)
- Deep-RL language ("learns" = falsifiable priors + gold eval, nothing more)
- GhostChef, DebtPilot, or any second product this weekend
- The FastAPI harness as the decision engine (n8n decides; Python is the test oracle)
- Compliance fear-pitch; Prosus/OLX/Mindtake logo-jacking; fake customers
- Fetching seller-supplied URLs; scraping outside the Apify-mediated feed

---

## 5. Risk-tier sentence (footer on every surface, unchanged)

> Limited-risk decision support for a reseller's **own** actions. We judge listings, not people. We skip and escalate; we never spend, never bind a contract, never touch a third party's listing. The reseller is the contracting party and signs.
