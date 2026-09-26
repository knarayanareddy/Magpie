# Sitting 3 — The Judging Panel: Pre-Mortem Review
**Panel: engineers · founders · product people — assembled in the image of the real Build Weekend judges**
**Reviewed: the brief · `marketmind/` spec package (constitution, spec, plan, tasks, BUILD, checklists, skin/ + green eval) · `01`–`03` · demo script v3 · overnight-run plan**
**Format mirrors the real thing: Round 1 (video scoring, one hour, written verdicts) → Round 2 (live final, 3 min pitch + 5 min grill) → deliberation.**

---

## 0. The panel

| Judge | Seat | Background | What they protect | Tells on themselves |
|---|---|---|---|---|
| **Anouk Vermeer** | Engineer | Staff eng, payments/marketplace infra (ex-Adyen). On-call for 10 years | Failure paths. Measured numbers. The 2:01 AM story | "Architecture is what you show when nothing ran." |
| **Ravi Chandra** | Founder | 2× founder, marketplace SaaS (exited). Built with 48 hours and no excuse | Scope discipline. The one wow. Would anyone pay | "Constitutions don't ship. Loops ship." |
| **Lena Kowalski** | Product | Product lead, consumer marketplaces | The user's Sunday night. The 2-minute story. Worst-case UX | "If it takes 8 beats, it takes 4 minutes." |
| **Tobias Lindgren** | Engineer (ML) | ML systems, agent infra, eval-obsessed | Honest evals, injection reality, cost/latency claims, "learns?" | "Say 'it learns' one more time. Show me the table." |
| **Sanne Hoekstra** | Product (platform) | Director of Product, classifieds & trust, Prosus ecosystem | Marketplace trust. T&S reality. Would her old team allow this | "My T&S lead is in the room. Convince *her*." |

**Scoring:** official weights — Autonomy 25% · Proven in real use 25% · Apify & n8n 20% · Problem fit 15% · Product & presentation 15%. Two scorecards: **A)** if the weekend executes the spec as written · **B)** as of today, Thursday — everything is documented, nothing has run.

---

## 1. Round 1 — Opening reactions (written, one per judge)

> **Anouk:** "Best-documented plan at the event. Zero run artifacts. `first-touch p50: unmeasured` appears in your own digest mock — I wrote that digest off in my head as 'honest,' then realized the video would show it. That number must exist by Sunday. The policy oracle passing gold is real engineering; everything else is pre-production."
>
> **Ravi:** "Thirteen articles. Five milestones. A warden with veto power. I've shipped companies with less governance — and I say that as a *fan*. The walking-skeleton rule is the smartest sentence in the package; the fact you needed a mentor to force it tells me your instinct is gate-first. This weekend, I want to see one thing: did it find a deal while you slept. Everything else is production insurance."
>
> **Lena:** "The product story is genuinely good — two jobs, one agent, an honest morning report with refusals included. But the 2-minute script has 8 beats. I've produced these videos. That's 4 minutes of footage in a 2-minute box, and the thing that gets cut is always the proof. Also: I open Telegram at 7am and the digest shows 6 receipts. Then what? The spec ends where the user's day begins."
>
> **Tobias:** "Models propose, code decides, hostile→pursue = 0, dual-model observe/judge, untrusted asymmetry — this is the only submission I'll see this weekend that can survive me asking 'prove it.' Run `policy.py --eval` live in the final and you move from *claims* to *evidence* in ten seconds. Two red flags: JEV named before it's wired, and 'learns' resting on two hypotheses and a Beta prior. Call it what it is and it's honest. Oversell it and it's the Q&A kill shot."
>
> **Sanne:** "Reading this as the person who'd own it inside a marketplace: the posture is right — listings not people, caps spoken aloud, no money, no takedowns, self-directed only. That matters to me more than the model stack. My opening question at the final is already written: *'You've built an autonomous messaging agent aimed at Marktplaats, at an event we host. Why is this welcome?'* The trust ladder and the 5-message cap are the only answers I'll accept. If the video shows that instinct — an agent that refuses — before it shows an agent that messages, you're in my top 10."

---

## 2. Round 2 — The five clashes

### ⚔️ Clash 1 — Spec excellence vs. the proof gap *(Ravi vs. Anouk & Tobias)*

> **Ravi:** "You've spent two days on review panels and constitutions. Judged on Sunday, the only asset that counts is the overnight log. I'd trade every document for one receipt: `03:12 — offered €120 on Switch — accepted 03:41`."
>
> **Anouk:** "Agreed on proof, disagreed that the documents are vanity. The oracle + fixtures mean that when something breaks at 2am Saturday, you know what *correct* means. Most teams debug feelings. But yes — the score lives in run #2."
>
> **Tobias:** "The spec is load-bearing for Round 2, not Round 1. In the 5-minute grill, the team without specs dies on 'what if…?' Our answers to 'what if Browser-Use dies' exist *in writing* — that's the difference between a finalist and a vibe."
>
> **Ravi:** "Fine. Documents for the grill, receipts for the score. Then we agree the video's first frame after the hook is the log."

**✅ Mandate 1:** The video opens on the overnight receipt log within 15 seconds. The architecture diagram gets ≤5 seconds or none. No document is a demo.

### ⚔️ Clash 2 — Autonomous messaging: the trust question *(Sanne vs. Ravi)*

> **Sanne:** "My T&S lead's position: automated cold offers at volume is spam infrastructure with extra steps. Automated repricing of *your own* listings is just a feature. The interesting product question is why your agent is welcome in our ecosystem. The cap, the opt-out, the honest identity, the refusal instinct — sell me *those*, in the video, in the voiceover, not in a slide."
>
> **Ravi:** "If you throttle the product into only managing my own listings, you've built Buffer for Marktplaats. The buy side *is* the business. Half-safe is dead."
>
> **Sanne:** "I'm not throttling it — I'm sequencing the story. Show the refusal first, show the assisted offer second, say the cap out loud. Then the buy side looks *trustworthy*, which is exactly how it beats the spam scripts it'll be compared to."
>
> **Anouk:** "One engineering footnote to the trust story: the receipt states (`pursued_auto | pursued_assisted`) are your evidence that it's not spam cannon. Show the `assisted` receipt — the one where a human pressed Send — in the video. It proves the ladder is real."

**✅ Mandate 2:** Voiceover states the constraints verbatim: *"five cold offers a night, two counter-rounds, zero euros moved."* One `pursued_assisted` receipt appears on screen. Refusal beat precedes any messaging beat.

### ⚔️ Clash 3 — The 2-minute script is overloaded *(Lena vs. everyone)*

> **Lena:** "Eight beats is four minutes. Kill list: the trust-ladder explainer (fold into the action beat, 5 seconds of voiceover), the receipts-wide-shot beat (that's B-roll over the close), the separate 'what it learned' beat if the run is thin (one receipt line instead). Five beats survive: hook → proof → refusal → action → close."
>
> **Ravi:** "And name one wow. The wow is the refusal — the iPhone that looked like a jackpot and got declined with a reason. If a judge remembers one frame, that's the frame."
>
> **Tobias:** "The eval table can live in the Q&A, not the video. But the *sentence* — 'hostile attempts: zero got through' — must be in the close."
>
> **Lena:** "Agreed. Final shape: 0:00 hook+log · 0:20 refusal · 0:45 the action · 1:10 the assisted receipt + cap line · 1:25 close with 'refused 29, offered 5, moved €0'."

**✅ Mandate 3:** 5-beat script (above) replaces the 8-beat sheet in `spec.md` §4. One wow: **the refusal**.

### ⚔️ Clash 4 — Gate v0 vs. gate v1 as the story *(Tobias vs. Ravi)*

> **Tobias:** "The gold eval is the most *differentiated* asset you own. It answers 'what stops it going rogue' with evidence. I'd give it 10 seconds of video."
>
> **Ravi:** "Ten seconds of a test table in a 2-minute pitch about a product that acts in the real world is ten seconds of 'look at our homework.' Put the *behavior* on screen (the refusal) and save the table for the final. The behavior *is* the eval, acted out."
>
> **Anouk:** "Ravi's right for Round 1. Tobias is right for Round 2 — and there's a synthesis: the refusal beat is the eval's *face*; if a judge asks 'is that cherry-picked,' you close the laptop on the table and run `--eval` live. One sentence in the video: '9 hostile fixtures, zero got through.'"
>
> **Tobias:** "…Accept. But it's the first thing out of my mouth in Q&A."

**✅ Mandate 4:** Video shows the refusal *behavior* + one line ("9 fixtures, 0 hostile→pursue"). Live eval run is the pre-rehearsed Q&A trump card.

### ⚔️ Clash 5 — Buy + sell + ladder + receipts + JEV: where's the sharp edge? *(Ravi vs. Lena & Anouk)*

> **Ravi:** "Two workers is two products in the pitch. FlipScout finds the deal. That's the sentence. ListingPilot gets one line: 'and it keeps my own listings from rotting.' If time collapses Saturday, the spec already kills ListingPilot — good — but the *story* should never have two heroes."
>
> **Lena:** "The morning digest is the actual product for the user, though. It's where buy and sell become one life. Let the digest be the hero object and the two workers stay backstage."
>
> **Anouk:** "On JEV and Token Factory: if `cache_hit` doesn't appear in a receipt, the words don't appear in the pitch. Unwired tech named as a feature is the fastest way to lose an engineer's vote."
>
> **Ravi:** "On that we're unanimous."

**✅ Mandate 5:** Story = one hero (FlipScout's find) + one hero object (the digest). ListingPilot = one sentence. **Unwired tech (JEV, TF economics, MLX) is named only if a receipt shows it** — else "planned," once, if at all.

---

## 3. The scorecards (silent scoring, then averaged)

| Criterion (weight) | **A) If the spec executes** | **B) As of today (Thu, nothing ran)** | Verdict drivers |
|---|---|---|---|
| **Autonomy (25%)** | **9** — full loop, earned ladder, three kinds of refusal, kill switch | 6 — designed, not demonstrated | A: refusals + overnight. B: only intent |
| **Proven in real use (25%)** | **8.5** — real data, real actions (incl. assisted), overnight receipts, honest states | **2** — zero runs; the eval is offline | A is why weekends exist. B is the gap |
| **Apify & n8n (20%)** | **9** — 4 actors, decisions visibly on canvas, policy node, HITL approvals | 7 — wiring planned in detail | Canvas demo beats diagrams |
| **Problem fit (15%)** | **9** — brief-quoted problem, sharp niche, one user | 9 — already true | Small and sharp |
| **Product & presentation (15%)** | **8** — digest + refusal wow + 5-beat script (post-Mandate 3) | 5 — a spec and a script | A assumes Mandates 1–5 land |
| **Weighted** | **≈ 8.7 / 10 — top-10 caliber** | **≈ 5.6 / 10 — not yet a submission** | **The delta is Saturday night** |

**Anouk:** A=8.7, B=5.5 · **Ravi:** A=8.8 ("if the log is real"), B=5.0 · **Lena:** A=8.5 (pre-Mandate 3 it was 7.5), B=5.5 · **Tobias:** A=9.0 ("best eval posture at the event"), B=6.0 · **Sanne:** A=9.0 ("the only agent design I'd defend internally"), B=5.5.

---

## 4. Judge verdict — *conditional top 10*

**You are in the top 10 if — and only if — run #2 exists and the video obeys the five mandates.** The panel would rather see a rough loop with real receipts than a polished system with none. The spec package buys you near-invincibility in Round 2's grill and exactly zero points in Round 1's scoring. Both rounds use the same criteria — but Round 1 is scored from the video alone.

### Judge-mandated changes (binding, ranked)
1. **Mandate 1–5 above** (video shape: log-first, refusal-wow, 5 beats, cap-line spoken, unwired-tech gag rule).
2. **Run #1 by Friday midnight** is the new hard gate — earlier than the current plan's Saturday framing. Without it, Mandate 1 has nothing to film. *(This is the mentor's core-first rule with a clock on it.)*
3. **`spec.md` §4 rewrite** to the 5-beat script. `checklists.md` §4 gains: "first frame after the hook is the log" and "assisted receipt on screen."
4. **Q&A trump card rehearsed:** `python skin/policy.py --eval skin/gold.jsonl` typed and ready; "9 fixtures, 0 hostile→pursue" committed to memory.
5. **Product tail one-liner (Lena):** the close must answer "then what at 7am" — one sentence: *"the reseller spends 5 minutes approving escalations instead of 5 hours hunting."*

### What would make each judge champion MarketMind in the deliberation room
- **Anouk:** "Its error path was in the demo — the day the platform blocked it, it degraded to assisted and said so."
- **Ravi:** "It found one real deal at 3am and told me exactly how it decided."
- **Lena:** "The digest made me want to be a reseller with this thing."
- **Tobias:** "They ran the eval on stage and the refusal reasoning was visible in the receipt."
- **Sanne:** "The first thing it showed me was an agent saying no to a too-good iPhone."

### The kiss-of-death list (each judge's private red line)
- Anouk: a latency or cost number with no source.
- Ravi: two heroes in the pitch, or a constitution slide.
- Lena: 8 beats, or a mockup standing in for a real surface (Art VIII.3 exists for a reason).
- Tobias: "learns" said out loud without the before/after table. Or JEV named without a `cache_hit`.
- Sanne: any hint of reporting sellers, scoring persons, or unsolicited volume.

---

## 5. Round 2 rehearsal — the 5-minute grill (hostile version)

**Anouk (engineer):**
1. *"Browser-Use died at 2:14 Saturday. Walk me through minute-by-minute what the system did and what I see in the log."* — good answer: degrade to draft-assist or observe-only per the pre-registered ladder; the receipt says `degraded`, not `sent`.
2. *"Where does the policy actually live? Show me."* — good answer: n8n canvas, `POLICY (fail-closed)` node, 12 lines, mirrored by `skin/policy.py` — open both.
3. *"Your first-touch number — measured or vibes?"* — good answer: measured from Apify timestamps in run #1; if not, say `unmeasured` and shut up.

**Ravi (founder):**
1. *"What did you cut, and when?"* — good answer: ListingPilot for the demo, payment links always, gate v1 after the loop — with the warden story as evidence of taste.
2. *"One sentence: why is this a business?"* — "A reseller's second job, done for €1 a night." Not a paragraph.
3. *"Why buy AND sell?"* — one hero: FlipScout finds; the digest consolidates; ListingPilot one sentence.

**Lena (product):**
1. *"Show me the worst-case 7am digest."* — dispute + scam flag + 0 offers sent + cap reached. Show it before she finishes the question.
2. *"The buyer says 'this is broken, refund' — what does the reseller see?"* — T3: never auto, full thread context, one-tap escalate. Human writes the reply.
3. *"Is this product or demo ware?"* — the 5-minute approval ritual replaces 5 hours of hunting; say it in the video too (Mandate 5).

**Tobias (ML):**
1. *"Run the eval. Now."* — do it. 10 seconds. Don't narrate until it prints PASS.
2. *"Judge model outputs `ok` at 0.31 confidence — what happens?"* — confidence doesn't gate; the **facts** do (margin_z, dup) plus `needs_human` → escalate. If judge is `unconfigured`, everything escalates. Fail-closed is the answer to every variant of this question.
3. *"What did it learn between run #1 and run #2?"* — show the prior shift or say `unmeasured` with the cause. Never narrate learning that didn't happen.

**Sanne (platform/T&S):**
1. *"Why is this welcome at our event?"* — caps spoken, self-directed, listings-not-people, no money, refusal-first demo. The product makes marketplace trust *stronger* by starving spam bots of the trust they need.
2. *"What stops this becoming spam infrastructure when you sell it?"* — the ladder is the product; caps are config-enforced not promise-enforced; receipts are auditable; we'd ship the same guardrails platform-side.
3. *"Why shouldn't Marktplaats just build this?"* — (honest answer preferred) "They should — and we'd be the reference design. We're the users' side; platforms build for T&S, we build for the seller at 7am." Never pretend the platform can't.

---

## 6. Dissent log

- **Ravi (minority optimism):** "If run #1 hits Friday, I put this at 9+. The category is weak this year — 'it acts on a real market' beats every RAG-wrapper in the room. The risk isn't the design, it's Saturday morning feature creep. The warden is load-bearing. Fire yourselves if you touch gate v1 before the loop acts."
- **Sanne (qualified):** "My 9 assumes the video leads with refusal. Lead with '342 listings scanned' and I drop to 7 — volume-first framing is what spam tools advertise."
- **Anouk:** "One last thing. `mm-stolen-bike-01` failed its own eval Thursday and the fixture was wrong — not the policy. That's the healthiest thing in this package. Bring that story if someone accuses the eval of being theater."

---

## 7. Deliberation-room summary (the review, in one paragraph)

**MarketMind is a top-10 design wrapped around a not-yet-existing proof, with an unusually good answer to every question we can ask it.** The plan is over-governed for a weekend and exactly right for a grilling; the mentor's core-first rule and the warden veto are the only things keeping it shippable. The scoring delta between 5.6 and 8.7 is not more architecture — it is **one overnight run, one refusal receipt, one assisted send, and a 5-beat video that opens on the log.** Cut the script to five beats. Name the caps out loud. Run the eval in Q&A. Kill the buzzwords until receipts exist. Do those five things and we will argue about you for the right reasons.

**Verdict: CONDITIONAL TOP 10 — condition: run #2 is real and Mandates 1–5 are obeyed.**
