# Domain Expert Panel — Critical Review & Debate
**Subjects: MarketMind (FlipScout + ListingPilot) · GhostChef · DebtPilot (control)**
**For: Build Weekend (Prosus) — autonomy is the one rule · Convened 24 Sept 2026**

> A five-expert panel was convened to red-team the two finalist ideas against the official judging criteria (Autonomy 25% · Proven in real use 25% · Apify & n8n 20% · Problem fit 15% · Product & presentation 15%). Below: opening assessments, five binding cross-examination clashes, a claims audit, and a **required-change list**. This is a revision document — treat the change list as binding before you build.

---

## 0. Panel roster & mandates

| Expert | Background | What they defend |
|---|---|---|
| **Iris van Dijk** — Autonomous Systems Architect | Agent orchestration, n8n/Apify pipelines at scale, reliability engineering | System integrity: does the autonomy loop actually close? Is it buildable in a weekend? Are the latency claims honest? |
| **Marc Bervoets** — Classifieds & Resale Operator | 15 yrs European classifieds (trust & safety + seller ops); power-reseller on Marktplaats since 2007 | Domain reality: how resellers actually work, how platforms fight automation, what a scam really looks like |
| **Sofia Almeida** — Food Delivery & Restaurant Ops | Ex-iFood city operations, promo & demand planning, restaurant playbooks | GhostChef realism: what promo surfaces actually exist, what restaurants will pay for, what "dead hour" economics really are |
| **Jonas Meijer** — Platform Risk & Compliance | Tech counsel, Amsterdam: ToS/scraping law, automated contracting, EU AI Act | Whether this gets you banned, fined, or booed off stage at a Prosus-hosted event |
| **Priya Raghavan** — Product & Demo Strategy | Ex-founder, hackathon judge alum, specialises in 2-minute video narrative | What wins Round 1 on Sunday 15:00: proof, story, and the single moment judges remember |

---

## 1. Round 1 — Opening assessments

Panel scores /10 per official criterion (weighted total in the last column).

| Idea | Autonomy (25%) | Proven real use (25%) | Apify & n8n (20%) | Problem fit (15%) | Product (15%) | **Weighted** |
|---|---|---|---|---|---|---|
| MarketMind v1 (as proposed) | 8.5 | 7.0 | 9.0 | 9.0 | 8.0 | **8.2** |
| GhostChef v1 (as proposed) | 8.0 | 4.5 | 8.5 | 9.0 | 7.5 | **7.3** |
| DebtPilot (control) | 7.0 | 5.0 | 5.0 | 7.0 | 7.0 | **6.1** |
| **MarketMind v2 (with this panel's changes)** | **9.5** | **8.5** | **9.0** | **9.5** | **9.0** | **9.1** |
| GhostChef v2 (channel-inverted, restaurant partner secured) | 8.5 | 7.0 | 8.0 | 8.5 | 8.0 | **8.0** |

**Opening one-liners:**

- **Iris:** "MarketMind's loop closes. GhostChef's loop closes *only if someone hands you an Uber Eats merchant login and a real restaurant* — that's not an architecture question, that's a dependency you don't control on Friday."
- **Marc:** "MarketMind describes my actual Tuesdays. But two of its hero demo beats are, frankly, scam bait, and the plan as written will happily chase them."
- **Sofia:** "GhostChef's problem statement is the truest pain on the board — €200–500/day of dead overhead is real. But the proposed *action surface* doesn't exist the way the doc claims. Fix the action, not the idea."
- **Jonas:** "MarketMind's outbound loop is a ToS and spam exposure running at a Prosus event, against a marketplace in the same commercial universe as their own OLX portfolio. There is a clean way to do this. The doc currently has the dirty way."
- **Priya:** "Both score well on fit because both literally quote the brief at itself — that's table stakes. The winner is whichever can *show logs of real decisions taken while nobody was watching*, plus **one visible refusal to act**. MarketMind is days ahead on the first; the second is up for grabs."

---

## 2. Round 2 — Cross-examination (the five clashes)

### ⚔️ Clash 1 — "Real actions" vs. real strangers' inboxes *(Priya vs. Jonas)*

> **Priya:** Criterion 2 is 25% of the score and says *show us the logs, bonus for a run that happened while you weren't watching*. A sanitised simulation tanks us. We need the agent to really message a real seller.
>
> **Jonas:** And Marktplaats' ToS prohibit automated contact and scraping at volume. The *safe* real actions are the ones on **your own account**: repricing your own listings, bumping them, replying to inbound buyers who contacted *you*. Those are ordinary account features you're allowed to use. Cold-outbound to strangers is where accounts get banned — and where a Prosus-hosted audience watches you spam Dutch sellers live on stage and win nothing.
>
> **Marc:** Correct. And practically: a fresh account firing templated offers gets shadow-limited within hours. I've seen it a hundred times. Your "overnight, 6 offers sent" plan dies at 2am and you demo a banned account on Sunday.
>
> **Priya:** Fine — but I won't accept zero outbound. The brief says "negotiate and close a sale **without the seller typing a word**."
>
> **Jonas:** Then bound it: a hard budget of cold outreach per day, honest copy, instant opt-out, approval-gated until the agent has *earned* autonomy in that category. That's not a compromise — that's literally the brief's second sentence: *"Autonomous doesn't mean uncontrolled."* Do that on purpose and my objection becomes your best slide.

**✅ Resolution — the Trust Ladder (binding):** real data + real decisions everywhere; real *actions* risk-tiered (see §5). Cold outbound is capped and gated; own-account actions carry the "real action" proof load; the caps themselves are demo material.

### ⚔️ Clash 2 — GhostChef's promo surface doesn't exist as drawn *(Sofia vs. Iris)*

> **Sofia:** "Browser-Use creates a flash promo on Uber Eats in minutes" is not a thing. Merchant marketing slots — sponsored placement, offer campaigns — have brand guardrails, geo rules and lead times of 24–48h. Nobody flips a flash discount at 14:52 because your agent had a feeling.
>
> **Iris:** And behind that sits merchant-manager auth plus bot detection. Your single core action is your single point of failure. That's why I rated real-use 4.5.
>
> **Sofia:** Meanwhile the surfaces that *are* instant — Google Business Profile posts, Instagram, WhatsApp Business broadcasts to a subscriber list, email — are owned by the restaurant, automatable cleanly, and measurably effective. I ran 2–5pm tea-time promos at iFood: 8–12% order lift on slow days, always via scheduled platform slots days in advance. The insight (predict the dead hour, size the discount, **suppress when a football match will fill you anyway**) is platform-independent. Keep the brain, swap the hands.
>
> **Iris:** Agreed. If the fallback is where the product actually lives, make it the product.

**✅ Resolution:** GhostChef v2 — "GhostChef Concierge": intelligence from delivery-ecosystem data (Apify: platform demand signals, competitor wait times, weather, events); actuation on **own channels** (Google Business, WhatsApp, Instagram, email + a flash-deal landing page with a promo code per run); Uber Eats dashboard = read-only + stretch goal only.

### ⚔️ Clash 3 — The 60-second loop is fiction *(Iris, unopposed)*

> **Iris:** An Apify actor is not a websocket. Each scheduled run has cold-start and fetch time — realistically 30–120s per cycle. A 60s cron that kicks off a fresh scrape run is theatre; at best you burn compute, at worst runs queue and overlap. Restate the loop honestly: **scheduled Apify run (every ~5 min) → dataset delta → n8n decision in seconds**. Then *measure* and claim the metric judges actually care about: **"median time from listing going live → offer sent: X minutes."** If that number is 6, say 6. A measured 6 beats an invented 1 every time — and I will ask you for the measurement.

**✅ Binding:** kill "scans every 60s" as a headline claim; publish a measured first-touch latency from real Apify run timestamps in the video.

### ⚔️ Clash 4 — "Learns" is currently decoration *(Priya & Iris vs. both leads)*

> **Priya:** The brief's definition of autonomous ends with "**learns**, and tells you what happened." Both docs list learning bullets — win rates, best offer %, response templates — with no falsifiable hypothesis and no before/after. Judges will ask "show me what it learned Friday vs. Saturday" and the room will go quiet.
>
> **Iris:** Concretise it: category-level acceptance priors (Beta counts are fine), offer-ratio band performance (70% vs 80% vs 90% of ask), bump-time performance. Pre-register two hypotheses on Friday, show the posterior table shift after the overnight run. That *is* learning. Calling it "RL" is how you lose the room.

**✅ Binding:** a **learning ledger** with pre-registered hypotheses and a visible before/after table in the video.

### ⚔️ Clash 5 — The two demo heroes are scam bait *(Marc, unanimously endorsed)*

> **Marc:** Let me kill the two best beats in the current demo script. Beat one: *"iPhone 14 listed at €320, comp €520, margin 62% — agent offers."* In the Dutch market that is the **textbook scam profile**: iPhones are the #1 fraudulent category, and a 62% margin is not a gift, it's a hook. Beat two: *"bike worth €800 listed at €400 — high-value opportunity, ask human to approve."* Nine times out of ten that is a stolen bike or an advance-fee scam. If your agent's instinct is "ask the human to approve messaging," you've built a crime-laundering pipeline with a rubber stamp. The correct behaviour is **refuse, flag, explain**.
>
> **Priya:** …Which is a *better* demo than the one you wrote. The single moment judges remember is the agent **declining a juicy deal**. Swap the beats: the too-good iPhone becomes the refusal; a boring, *plausible* deal becomes the action.
>
> **Marc:** Exactly. A Switch at €140 against €180 comps — 22% margin after fees and pickup friction — is what a real deal looks like. Realistic margins make you credible, not unambitious. Demo on consoles and camera gear; keep phones and bikes in the config as the **always-human** categories.

**✅ Binding:** demo-script rewrite (§7) + concrete anti-scam heuristics (§5).

---

## 3. Claims audit *(Iris & Marc)*

| Claim in current docs | Verdict | Fix |
|---|---|---|
| "Scans Marktplaats every 60s" | ⚠️ **Measure or soften** | "~5-min scheduled runs; measured first-touch: X min (see run timestamps)" |
| "Vision AI prices item from photos" | ⚠️ **Overclaimed** | Vision = **triage** (condition, colourway, defects, duplicate/scam cues). eBay **sold comps are ground truth**. Never quote a photo-derived absolute price. |
| "iPhone 14 at €320 → 62% margin → offer" (demo beat) | ❌ **Cut — harmful** | Becomes the scam-refusal beat |
| "High-value opportunity: €800 bike for €400" | ❌ **Cut — harmful** | Becomes stolen-goods / too-good-to-be-true refusal |
| "342 listings scanned overnight, 300+ decisions" | ✅ Keep, but | Volume is only proof if the *refusals and reasons* are visible. Lead with decision quality. |
| "2 deals accepted overnight" | ⚠️ **Luck-dependent** | Never promise outcomes. Script says "offers accepted where it happened"; show whatever the logs say. Pre-arranged counterparties (your own second account) guarantee at least one full negotiate-and-close loop with zero third-party risk. |
| "Sends payment link → close the sale" | ❌ **Cut** | Payments = regulated surface + demo risk. The agent's mandate ends at the handshake ("deal agreed, pickup via Marktplaats' normal flow"). |
| "Auto-negotiate within preset max price" (unbounded) | ⚠️ **Tighten** | Max **2 counter-rounds**, hard price ceiling, trust-budget cost per round. |
| "GhostChef: flash promo on Uber Eats" | ❌ **Cut as core** | Relegated to stretch. Own-channel actuation is the product (Clash 2). |
| "€450 extra revenue this week" | ⚠️ **Unverifiable** | One promo code per run; claim **measured incremental orders/redemptions**, or "n pending redemptions" — nothing else. |
| "Resellers spend 3–5 h/day" / "restaurants lose €200–500/day" | ✅ Keep as framing | Label as industry-range estimates, not your measurements. |

---

## 4. Verdict — binding change list

### 🔴 MUST-FIX (before you write a line of workflow)

1. **Trust Ladder replaces ad-hoc escalation.** The ">€200 → ask human" rule becomes a *calibrated autonomy budget* the agent earns:
   - **T0 — Observe (always free):** scan, price, flag, report.
   - **T1 — Own-account actions (auto):** reprice/bump *your* listings, reply to *inbound* buyers of your listings with guardrails.
   - **T2 — Cold outreach (capped):** ≤5 offers/day/night, honest copy, instant opt-out, approval-gated per offer **until** the category acceptance-prior is established (e.g. 5 observed outcomes), then auto within caps.
   - **T3 — Never auto (always human):** deals >€200, high-risk categories (phones, bikes/e-bikes — theft & fraud rates), any dispute or "this is broken" message, anything involving money movement, anything the anti-scam heuristics flag.
   The ladder *is* the "knows what it can handle alone, when to bring in a human, when to stop" criterion — say those words in the video.
2. **Anti-scam heuristics, made concrete** (all in n8n, deterministic):
   - **Too-good filter:** implied margin > ~50–60% vs comps ⇒ **suspicion, not excitement** (z-score vs. category comp mean).
   - **Duplicate detection:** perceptual-hash of listing photos vs. recent scraped set + reverse-image check ⇒ stolen-photo detection. Cache seen-hashes so re-posts don't trigger double offers.
   - **Seller signals:** account age, rating count, price-only-in-description patterns, off-platform payment asks (Tikkie/bank transfer urgency) ⇒ auto-flag & skip.
3. **Demo category = consoles / camera gear** (credible 15–35% margins, deep eBay sold-comps history, low theft association). Phones & bikes appear **only** as the approval-required / refusal examples.
4. **Loop-latency honesty (Clash 3):** measured "listing live → offer sent" median in the video; no 60s fiction.
5. **Learning ledger (Clash 4):** two pre-registered hypotheses + before/after priors table. Example: *H1 — offers at ≤80% of ask get ≥25% acceptance in games; H2 — evening bumps outperform morning bumps.*
6. **Pre-registered fallback ladder**, printed on-screen in the video so judges see you planned for failure:
   - Platform blocks Browser-Use ⇒ agent drafts message + opens page, human presses Send ("90% autonomous" mode) — demo the navigation either way.
   - Apify actor down ⇒ cached comps + transparent "grounding stale" banner; agent **degrades to observe-only** (it refuses to price on stale data — another stop-moment).
   - Live demo blocked (venue Wi-Fi, login wall) ⇒ replay of the real overnight logs + recorded browser session. Never improvise Sunday morning.
7. **n8n owns the decisions; Apify owns the data.** Policy caps, trust-ladder state and stop-rules live in a visible n8n Code/policy node (deterministic, fail-closed — the Judge will ask "where are the rules?"). LLMs handle only language: intent classification, offer drafting, negotiation tone. Keep a one-page inventory: *which Apify actors feed which n8n nodes* (see §6) — that's your 20%-criterion Q&A sheet.
8. **Overnight run protocol:** Friday 22:00 → Saturday 08:00 with full console + Airtable + Telegram capture. Success criteria defined *before* the run (N evaluated, ≥1 full negotiate loop, ≥1 refusal with reason, learning ledger shifted). This is your 25% "bonus points" shot.

### 🟡 SHOULD-FIX

- One config knob for categories, but the **story** is one sharp niche ("your retro-games desk") — criterion 4 says it outright: *small and sharp beats big and generic*.
- Competitor-price monitoring: 3 competitors per category, not "the market".
- Telegram morning digest is the product's face — design it before the workflow; it's 40% of the demo.
- Put one line in the video: *"We cap autonomous outreach at 5 per night."* Judges read constraint-maturity as engineering maturity.

### ⛔ CUT (without ceremony)

- Payment links / "close the sale" through money movement. The agent ends at the handshake.
- Unbounded auto-negotiation (fixed at 2 counter-rounds).
- The iPhone and the €400 bike as "opportunities".
- GhostChef's Uber-Eats-flash-promo as core actuation.
- Any "300+ decisions" flex that hides decision quality.
- Deep-RL language anywhere.

---

## 5. Revised concepts (v2 one-pagers)

### 🏪 MarketMind v2 — *"The trust-calibrated reseller operator"*
Two workers, one supervisor, one earned-trust ladder. **FlipScout** notices (Apify: Marktplaats feed + eBay sold comps + Google verification) and decides (comps-first pricing, vision-triage, anti-scam gate). **ListingPilot** notices (your listings + 3 competitors + inbound mail) and decides (stale ⇒ reprice/bump; intent-classified inbound ⇒ reply/counter/escalate). **Both** act through Browser-Use only within their tier: T1 repricing/replies/bumps run autonomously tonight; T2 cold offers run capped and gated until priors are earned; T3 (disputes, >€200, phones/bikes, scam flags) always halts with a reasoned Telegram escalation. It learns category acceptance priors and bump/offer-band performance, and every morning says what it did — including what it **refused**. *Deltas vs v1: Trust Ladder, anti-scam gate, scam-bait beats inverted, 2-round negotiation cap, payment-link cut, measured first-touch latency, learning ledger.*

### 🍳 GhostChef v2 — *"GhostChef Concierge"* **(backup — only if a real restaurant partner signs up by Friday noon)**
Same brain: Apify reads delivery-platform demand signals, competitor wait times, weather, local events; n8n predicts the dead hour, sizes a discount, and **suppresses** when an event will fill seats (the celebrated "stop" move — now powered by a real events feed with a transparent threshold rule, e.g. *event within 2 km & ≥2,000 expected within 2h of the window ⇒ suppress*). New hands: promo goes out on the restaurant's own channels — Google Business post, WhatsApp broadcast, Instagram, email + a flash-deal page with **one promo code per run** (which is also your causal measurement for the learning loop: redemptions ⇒ elasticity per daypart ⇒ stop promos that cannibalise dinner). *Deltas vs v1: actuation moved off Uber Eats (stretch only), event-suppression made falsifiable, revenue claims replaced with code-attributed measurements, no 78ms-latency story — this product's SLA is minutes and that is fine.*

### 💸 DebtPilot — held in reserve (panel: 30-second disposition)
Safe but flat on Apify/n8n depth (2 actors) and "real use" needs consenting debtors. Only revive if both finalists hit platform-blockade on Saturday. Its dispute-escalation beat is stealable for MarketMind's T3 tier.

---

## 6. Tech-stack answer sheet *(for "what actually powers this?" questions)*

| Layer | Tool | Exactly what it does | Judges' question it answers |
|---|---|---|---|
| Data in | **Apify** — 1) Marktplaats listings actor 2) eBay sold-comps actor 3) own-listings monitor actor 4) Google Search actor (brand/model verification + seller lookups) [+ events/weather actor for GhostChef] | Scheduled runs → datasets → webhook/poll into n8n; **run history is literally "the logs"** | 20% Apify weight; "real-world data" |
| Orchestration & decisions | **n8n** — Supervisor AI Agent + two sub-workflow tools (FlipScout worker, ListingPilot worker); cron & webhook triggers; deterministic **policy node** (caps, trust ladder, fail-closed stops) | The decisions visibly live on the canvas; execution log is the audit trail you show in the video | 20% n8n weight; "where are the rules?" |
| Acting | **Browser-Use Cloud** (HTTP API from n8n) | Authenticated sessions: send offer/reply, edit price, bump listing; **session recordings double as demo footage**; degrades to draft-and-hand-off when blocked | "It takes real actions" |
| Language | GPT-4o-mini / Haiku-class LLM | Intent classification ("serious offer / lowball / dispute"), negotiation drafting (max 2 counter-rounds), report writing | "Where is the AI vs. rules?" — AI for language, rules for money and stops |
| Vision | Qwen-VL / GPT-4o vision | Photo **triage** only: condition, colourway, defects, duplicate/scam cues | Defuses "how does it price from photos?" |
| Memory & learning | **Airtable** | Deal log, trust-ladder state, learning priors (before/after), audit rows | "Show me what it learned" |
| Human-on-the-loop | **Telegram** | Morning digest + approval buttons (T2 offers pre-earned-prior, T3 escalations) | "When does a human get involved?" |

If asked *"why n8n and not a Python script?"*: decisions must be inspectable and editable by a non-engineer at 3am without a deploy; the Apify⇄n8n wiring is exactly the platform pair the brief asks for; and the execution log **is** the product's accountability story.

---

## 7. Demo script v2 — 2-minute beat sheet *(Priya)*

| Time | Beat | Screen shows |
|---|---|---|
| 0:00 | "Resellers run two full-time jobs: hunting deals and babysitting their own listings. MarketMind runs both — here's its **honest** overnight log." | Telegram digest opening |
| 0:12 | **Proof:** 342 evaluated · offers sent (capped at 5) · 3 of *your* listings repriced · 4 inbound buyers handled · **2 refused with reasons** | Airtable + n8n execution log, timestamps visible |
| 0:28 | **The action:** plausible Switch deal (€140 vs €180 comps, 22% margin). Agent navigates Marktplaats, sends the offer — offer counter is at 1/2. | Browser-Use recording |
| 0:45 | **The earn-your-trust move:** reprices your stale listing €180→€155, bumps it, replies to an inbound buyer — all T1, no approval needed | Browser-Use recording |
| 1:00 | **THE MOMENT — the refusal:** iPhone 14 at €320 (62% "margin"), photos match a listing from Rotterdam last week (pHash hit). Agent: *"Too good + duplicate photos = probable scam. Skipped. Reason logged."* Also: the €800-for-€400 bike → T3, routed to you, not chased. | Decision log with reasoning |
| 1:20 | **What it learned:** acceptance priors before → after the night; it just raised the auto-approval threshold in Games from 3 to 5 required outcomes. | Learning ledger |
| 1:35 | "47 decisions while the reseller slept — including the ones it refused to make." | Wide shot of the canvas + digest |

---

## 8. Panel Q&A ammunition *(the seven hardest questions — with answers)*

1. **"Isn't this just scraping and spam with extra steps?"** — "Scanning is read-only intelligence; every *action* is risk-tiered. Own-account actions run free, cold outreach is capped at 5/night and gatekept until category priors are earned, and disputes and high-risk categories never automate. The constraints are the product."
2. **"What did it actually do while you slept?"** — Go straight to timestamped Airtable rows + n8n executions + the Telegram digest. Numbers straight from logs; nothing pre-written.
3. **"How does it 'learn' — really?"** — "Falsifiable priors, not RL. We pre-registered H1 and H2 on Friday; this is the before/after table. The threshold it changed on its own is on screen."
4. **"What if Marktplaats blocks you mid-demo?"** — "Three-tier fallback, pre-registered: draft-and-Send handoff (still shows full navigation) → replayed real overnight logs → recorded session. The agent also degrades to observe-only on stale data rather than acting blind."
5. **"Why is this better than one GPT-4o call with a browser tool?"** — "Monolithic agents improvise; ours has a deterministic fail-closed policy layer for money, caps and stops — language models propose, rules dispose. That's why it can be trusted with a real account."
6. **"You're at a Prosus event targeting Marktplaats — should we be flattered or worried?"** — "The trust ladder was designed *because* marketplaces' trust is the asset. We cap outreach, honor opt-outs, never touch payments, and escalate disputes. We'd ship the same guardrails inside OLX tomorrow." *(have this one memorised — someone will ask)*
7. **(to GhostChef, if revived) "Where does the promo actually run?"** — "Own channels with per-run promo codes — which is also our measurement instrument. Uber Eats is intelligence and a stretch action, not the dependency."

---

## 9. Dissent log & final vote

- **Sofia (dissent):** "If a real restaurant partner appears by Friday noon, GhostChef Concierge outscores MarketMind on revenue clarity and on the nuance of its suppression decision. I'm voting *conditional-GhostChef* — and if that condition isn't met by Friday 12:00, my vote moves to MarketMind v2 and I'll build the events-suppression module for it as a second stop-moment."
- **Jonas (qualified assent):** "MarketMind v2 **only** with the Trust Ladder and the cut list executed. v1 as drafted is a no from me."
- **Iris, Marc, Priya:** MarketMind v2, unqualified.

**Final: 4–1 — build MarketMind v2.** Re-open GhostChef only on the Friday-noon condition. DebtPilot stays in the drawer.

### Why this wins the rubric, in one line each
- **Autonomy 25%:** full notice→decide→act→learn→report loop, with an *earned*-autonomy ladder and three kinds of refusal — the brief's definition, verbatim.
- **Proven real use 25%:** real Marktplaats + eBay data, real own-account actions, overnight run with logs, one self-handled failure (scam skip / stale-data degradation).
- **Apify & n8n 20%:** 4 actors feeding visible n8n decision workflows with a deterministic policy node and execution-log audit trail.
- **Problem fit 15%:** the brief's own classifieds sentence, narrowed to one sharp niche.
- **Product 15%:** Telegram digest as the face, one memorable refusal beat, pre-registered fallbacks on screen.

---

## 10. Revised 72-hour timeline *(Iris & Priya)*

| When | What |
|---|---|
| **Thu PM** | Lock scope (FlipScout + ListingPilot, one category). Pre-register H1/H2. List 5 own items on Marktplaats (camera gear/games). Get second account + one friend account ready as *pre-arranged counterparties* for a guaranteed full negotiation loop. |
| **Fri AM** | Apify actors up (listings, comps, own-listings, search). Verify actor cadence & measure one full run cycle (**this kills the 60s myth — get real numbers**). |
| **Fri PM** | n8n: supervisor + policy node (Trust Ladder) + FlipScout decide-path. GhostChef condition expires 12:00. |
| **Fri 22:00** | **Overnight run #1** (observe-only + T1). Capture everything. |
| **Sat AM** | Browser-Use actions (T1 reprice/bump/reply live; T2 offer to pre-arranged counterparty). Fix what run #1 exposed. |
| **Sat PM** | Telegram digest design + learning ledger wiring. Scam-heuristics tuning with the iPhone/bike fixtures. |
| **Sat 22:00** | **Overnight run #2 — the hero run** (full loop within trust tiers). |
| **Sun AM** | Record the 2-min video from real logs (beat sheet §7). Fallback recordings done **before** noon. |
| **Sun 15:00** | Submit. 16:15 — if in top 10: pitch the loop, demo the refusal, flash the before/after ledger. |

---
*Proceedings closed. Change list is binding. Dissent recorded. Go build.*
