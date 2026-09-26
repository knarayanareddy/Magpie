# MarketMind — Operational Checklists

Print these. Tick them. Unticked boxes on Sunday are lost points.

---

## §1 Kickoff prep (T-2 → T-1, T04) — 60 min (create accounts T-3 to warm trust)
- [ ] `NAMED_RESELLER` consented in writing (name + role). No consent ⇒ `unset` shown, own-accounts only (Art III).
- [ ] Dedicated demo Marktplaats account created (not personal). Second account + 1 consented friend ready as **pre-arranged counterparties**.
- [ ] 5 own items listed (consoles/camera gear) — ListingPilot now has real inventory to manage.
- [ ] Niche locked: consoles/camera gear. Phones/bikes configured as T3-only examples.
- [ ] H1/H2 pre-registered and written down: H1 offers ≤80% of ask accepted ≥25% in Games · H2 evening bumps > morning bumps.
- [ ] Keys probed: Apify ✓/✗ · n8n ✓/✗ · Telegram ✓/✗ · Airtable ✓/✗ · **TF probe recorded `live|fallback`** (Art II.3).
- [ ] Env shape per `BUILD.md` §2 set; `MAX_COLD_OUTREACH=5`; tier JSON loaded from `plan.md` §4.

## §2 Milestone gate checks (Core-First Warden)
- [ ] **M0 done-done:** a stranger watching the run would say "it acts." (T08) — then and only then continue.
- [ ] **M1 done-done:** loop ran unattended ≥30 min; `/pause` tested live; first-touch measured. (T09–T15)
- [ ] **WARDEN SIGN-OFF here — no M2 work exists before this tick**
- [ ] **M2 done-done:** gold eval green (0 hostile→pursue); receipts visible; injection one-click repro. (T16–T19)

## §3 Overnight run — ONE hero run: **Sat 26 Sep 22:00** (T15=T22) — arm before sleep (Run #2)
- [ ] Config frozen (no edits during run). Caps armed: 5 cold/night, 2 counter-rounds, 1 action/listing/24h.
- [ ] `/pause` reachable from phone. Friend counterparties briefed ("the bot may message you tonight").
- [ ] Capture on: Apify run history · n8n executions · Airtable rows · Telegram thread · Browser-Use session recordings.
- [ ] Watch window set (first 20 min live) then **walk away** — the "while you weren't watching" bonus requires it.
- [ ] Success criteria written before sleeping: ≥1 full notice→decide→act→report cycle · ≥1 refusal with reason · ≥1 receipt row per decision.

## §4 D2 demo-day / video (Sun 27 Sep, T24)
- [ ] Fallback recordings exist **before noon** (replay of run #2 + draft-assist path) — Art VIII.3.
- [ ] **First frame after the hook is the overnight log** (judge Mandate 1). Architecture ≤5s or none.
- [ ] 5-beat script (`spec.md` §4) followed; **the refusal is the wow** and precedes any messaging beat.
- [ ] **One `pursued_assisted` receipt on screen**; constraints spoken verbatim: "five cold offers a night, two counter-rounds, zero euros moved." (Mandate 2)
- [ ] Three ladder beats present: one auto (T1) · one capped/assisted (T2) · one refusal (T3/hostile).
- [ ] Constraints said out loud: "five cold offers a night, two counter-rounds, zero euros moved."
- [ ] Every on-screen number traced to a receipt/log/eval cell; `unmeasured` where honest.
- [ ] Video ≤ 2:00 · audio checked · named human + risk-tier sentence visible.

## §5 Submission (T25)
- [ ] Video submitted before **Sun 27 Sep 15:00 (D2)**.
- [ ] Logs export attached/linked (receipts CSV or Airtable view + n8n execution screenshots).
- [ ] Repo/links tidy; no keys anywhere (Art XI).
- [ ] Killed-list glance (`ORIGIN.md` §4): nothing revived, nothing faked.

## §6 Claims audit (T23 — run once before recording)
- [ ] "Scans every 60s" → replaced with measured cadence + first-touch p50 (or `unmeasured`).
- [ ] "2 deals accepted overnight" → "here's what the logs say" (no promised outcomes).
- [ ] €-numbers → measured (promo-code/priors logic) or labelled industry-range.
- [ ] `drafted` never described as "sent." `assisted` always shows the human press.
- [ ] Cost/latency claims match the Art IV table; no borrowed MenuSafe ms-budgets (wrong SLA — minutes, measured).

## §7 Q&A drill (live final, ~5 min) — answers in `../01` §8 + `../02` §7
**RED LINES (kiss-of-death, sitting 3):** unsourced numbers · two heroes in the pitch · "learns" said without the before/after table · unwired tech named (JEV/TF/MLX without a `cache_hit` receipt) · volume-led framing (never open with "342 scanned") · any hint of scoring persons, reporting sellers, or volume messaging.
- [ ] **TRUMP CARD (pre-typed, rehearsed): `python skin/policy.py --eval skin/gold.jsonl`** — run it live, say only "9 fixtures, 0 hostile→pursue" after PASS (6 hostile of 9 — exact counts). Do not narrate until it prints.
- [ ] "Isn't this just scraping + spam?" → trust ladder, caps, self-directed only.
- [ ] "What did it do while you slept?" → receipts, timestamps, refusals included.
- [ ] "How does it learn?" → falsifiable priors + gold eval. No RL.
- [ ] "What if it's blocked/it breaks?" → pre-registered fallback ladder, shown on screen.
- [ ] "Why n8n, not a script?" → decisions visible/editable/auditable; execution log = accountability.
- [ ] "Why does a buyer bot carry a T&S gate?" → *"the moment an agent acts on the open market, trust and safety is the product."*
- [ ] **"How do you know you didn't over-engineer the gate?"** → *"Article I vetoed gate work until the loop closed; run #1 happened on gate v0 — three rules. The gate is 12 lines of policy and closed sets we already had."*
- [ ] **"How does it scale / why poll every 5 min?"** → *"Dual topology: `wf-m0/m1` runs anywhere on vanilla n8n via cron. For enterprise scale, `wf-m2-event-driven` uses the `@apify/n8n-nodes-apify` trigger (`ACTOR.RUN.SUCCEEDED`) for event-driven deal arrival as soon as a crawl finishes, with async polling as documented network fallback."*
- [ ] "Who is liable if it offers on a stolen bike?" → it can't decide about people; escalations are the human's call; payments don't exist; the reseller signs.
- [ ] "Prove hostile→pursue = 0" → run the eval on stage/laptop in 10s (`python skin/policy.py --eval skin/gold.jsonl`).
