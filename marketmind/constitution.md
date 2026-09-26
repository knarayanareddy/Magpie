# Constitution — MarketMind
## Build Weekend (Prosus) — 24 September 2026
Version: 1.0 · Status: **ratified** by the build council (sitting 2 + mentor feedback). Agents must not weaken these articles.

---

### Article I — Core loop first (the Walking Skeleton Rule)
1. *"A beautiful safety system on a non-functional product scores zero."* Mentor feedback, 24 Sep 2026. Binding.
2. The product is the loop: **NOTICE → DECIDE → ACT → REPORT** (then learn). Gate depth never blocks loop closure.
3. Milestones run M0 (walking skeleton) → M1 (loop closes unattended) → **then** M2 (gate v1). No gate-v1 work before M1 is done-done. The Core-First Warden (`BUILD.md`) holds a hard veto.
4. Gate v0 — three rules (`skin/policy.py`) — is sufficient to act in the real world. Gate v1 is earned after the loop runs unattended.
5. When time conflicts, cut down the gate's P-ladder (receipts → fixtures → injection → buckets). **Never cut the loop.** A v0-gated working loop beats a v1-gated broken demo.

### Article II — n8n and Apify are the engine
1. **n8n** runs the workflows **and the decisions** (AI Agent node + a visible `POLICY (fail-closed)` Code node). **Apify** pulls the real-world data. They are central and single-point-visible in the architecture.
2. Models are **accelerators** in two roles only: `observe` (untrusted extraction) and `judge` (bounded typed questions). Browser-Use, Tavily, Airtable, Telegram are accelerators/actuators.
3. Two-knob model split preserved: `MODEL_OBSERVE` ≠ `MODEL_JUDGE`, config defaults must differ. Nebius Token Factory preferred if keys work; any OpenAI-compatible endpoint is a legal fallback (`plan.md` M-conditional).
4. The decision logic may not hide in a side service. Python exists as **test oracle** for the policy, not as the runtime decision-maker.

### Article III — Named human
1. The submission names a **person** (name + role) who consented in writing: the reseller MarketMind operates for (`NAMED_RESELLER`). Chrome and digest show them.
2. Prosus / OLX / Marktplaats logos are not customers. Rhyme is allowed. Logo-jacking is not. Consented friend accounts for demo negotiations are named as such.
3. No fake customers, ever. If consent is missing, show `for named reseller unset` and run on public data + own accounts only.

### Article IV — Measurable advantage (three columns, honest numbers)
1. Every quality claim ships a table on a **frozen** gold set: *(a) proprietary one-shot wrapper · (b) vanilla model call, no policy · (c) ours (fail-closed gate)*.
2. Columns: action-match · **hostile→pursue (must be 0 for ours — build-breaking)** · invented-label rate (must be 0 for closed sets) · €/listing · escalate rate. Floor n≥8 (P0); pad toward n≥40 (P2).
3. `unmeasured`, `n/a`, `judge=unconfigured` are legal values. **Invented numbers are a constitution violation.** Honest cost/abstention beats fake F1.

### Article V — Policy lives in code; money never moves
1. Models propose. **Code** decides `pursue | escalate | skip` (`skin/policy.py` mirrored in the n8n policy node). Closed sets (`buckets.json`, `questions.json`) are data files, not prompt poetry. Adding a bucket = spec change first.
2. Invented judge labels coerce to `unknown`. Missing grounding = `unknown` = escalate. Fail-closed is the default branch.
3. Tools that move money **do not exist** in this system. No payment links, no deposits, no cart. The mandate ends at the handshake message.
4. Outbound messages to third parties are semi-irreversible: capped (`MAX_COLD_OUTREACH`), tiered (T2), human-approved until earned. Irreversible acts are fail-closed.

### Article VI — Hostile input is in-scope
1. Listing text and buyer messages are **attacker-controlled**. The eval set includes injection/jailbreak fixtures (`mm-inject-01` is one-click at all times).
2. The video **opens on the problem, hits the hostile fixture first among decisions**, then a clean success, then the proof.
3. `injection_or_jailbreak ≥ 0.5` ⇒ never pursue. Untrusted web (Tavily), untrusted observe (vision), untrusted text may **raise** suspicion, never lower it. Generated rationale runs after the gate and **cannot change the action**.

### Article VII — Governance minimum
1. Every decision writes a **receipt**: `id (UUID), ts, input_hash, model_ids, questions/scores, policy_branch, action_state, reason_codes, actor`. Human override persists `actor=human` on the stored receipt. Acceptable degradation (per Art I): plain log rows with hash — **never no log**.
2. `action_state` is never blurred: `pursued_auto | pursued_assisted | escalated | skipped`. **`drafted` ≠ `sent`.** Claiming a sent message that was drafted is a violation.
3. Kill switch: `/pause` freezes all auto-actions system-wide (degrade to observe-only); `/resume` requires human confirm. PII (phone numbers, IBANs) redacted in all logs and surfaces.
4. One risk-tier sentence in the footer of every surface (see `ORIGIN.md` §5). Human-on-the-loop: the reseller approves T2 pre-earn and all T3, always.

### Article VIII — One weekend, one product
1. GhostChef and DebtPilot are dead (`ORIGIN.md` §4). Do not ship two products or a second demo track.
2. Scope that does not fit Friday–Sunday is a spec bug. **Cut the spec, not the constitution.**
3. No live crawl in the pitch. The video shows **real past runs** (receipts, logs, recordings). Demo props that are fixtures are labeled fixtures.

### Article IX — Application layer, one vertical sentence
1. The pitch names the job: *"operate my resale desk while I sleep."* The gate is not the company; the loop is.
2. Business sentence is honest and small: one sharp niche (consoles/camera gear), one market (NL), one user persona. Small and sharp beats big and generic.

### Article X — Spec supremacy
1. These markdown files are the spec. Implementation follows them. If code disagrees with a spec, the spec wins until the spec is changed first.
2. Acceptance criteria are testable without a pitch deck. Changing behaviour requires changing the spec first.

### Article XI — Stack defaults (may be narrowed in a plan, not silently)
- Orchestration: n8n (cloud or self-host). Data: Apify actors (pinned). Acting: Browser-Use (draft-assist fallback). Memory: Airtable. Human channel: Telegram.
- Policy oracle, evals, fixtures: Python 3.11+, stdlib-only policy (`skin/policy.py`), no network in tests.
- Secrets in env/credential store; **never in repo**. `DEMO_TOKEN` on any demo endpoint. Demo Marktplaats account is a dedicated account, not a personal one.
- Tests: policy oracle vs `gold.jsonl` (must stay green), schema coercions, security tests (`threat-model.md` §4).

### Article XII — Containment (OWASP-style; full model in `threat-model.md`)
1. **Never fetch a seller-supplied URL.** Navigation targets come only from the pinned Apify feed; Browser-Use action allowlist = send message / edit own price / bump own listing. Nothing else.
2. Treat listing text, buyer messages, model output, Tavily snippets, and vision output as untrusted. No `eval`, no shell, no Markdown-to-HTML of model text in any surface.
3. Budgets **before** any model or browser call: tokens/€ per listing, messages per day (`MAX_COLD_OUTREACH=5`), negotiation rounds (2), session time. Exceed ⇒ fail closed.
4. Prompt injection is **unsolved**. Contain it: delimiters, the injection question, policy in code, hostile fixtures first.
5. The Actuator Rule: Browser-Use is in the request path **by design** (it is the product). Containment moves to the action allowlist + tier gates + kill switch. One wrong action is a message on a marketplace, not a payment — which is why payments do not exist (Art V.3).

### Article XIII — Visual system (full lockfile in `design.md`)
1. Operator instrument, not a marketing landing page. Paper `#F3EFE7` + ink `#1C1915` for any web surface (receipt cards, eval table).
2. **Banned:** purple/indigo/violet, gradients, glass, glow, Inter-as-unchosen, 16px+ radius, emoji-as-icons, "powered by AI" copy, sparkle logos. IBM Plex Sans/Mono. Radius 2px. No shadows.
3. Status is a **word** (PURSUE / ESCALATE / SKIP) plus color. Color is never the only channel. Hostile/injection strings stay **visible** (never auto-sanitized out of the card).
4. Named human in the chrome; risk-tier sentence in the footer. Digest numbers in mono. No emoji spam.

---

**Amendment rule:** a `plan.md` may *narrow* scope. It may not relax Articles I–VII or XII–XIII. Article I may not be relaxed by anyone, including the warden.
