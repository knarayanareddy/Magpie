# HUMAN-PLAYBOOK — everything code can't do (Thu 24 → Sun 27 Sep 2026)

> The code is built, tested, and committed. **This file is the only work left: accounts, listings, credits, keys, and four time-boxed moments.** Tick as you go. Every step has: ⏱ estimate · ✅ done-when · 🆘 fallback.
> Authority order if anything conflicts: `constitution.md` > `plan.md` §6 stop-the-lines > this playbook.

---

## PHASE 0 — Thursday 24 Sep (or Fri morning) — 45 min total
*Why today: fresh marketplace accounts need 48h of light activity before an agent touches them; consent and freezes are one-time events that must not be rushed on Saturday.*

### 0.1 Create + warm the 3 marketplace accounts — ⏱ 15 min today, 2 min/day after
Go to **https://www.marktplaats.nl** → *Registreren* (email + username + password; verify the email link; add phone if prompted — one phone can usually verify multiple accounts, else use a second number):

| Account | Role | Name in the system |
|---|---|---|
| **A — the reseller** | MarketMind operates this one (owns the 5 listings) | `NAMED_RESELLER` (must match `kickoff/consent.txt`) |
| **B — counterparty #1** | Your second account — the seller you send pre-arranged offers to | named "pre-arranged counterparty (own)", Art III.2 |
| **C — counterparty #2** | One consented friend/family member's account | named as such, Art III.2 |

**Warming ritual (today AND Friday, ~2 min per account):** log in, browse 3–5 listings in *Games & Consoles* / *Fotografie*, favourite/save 2–3 items. From B and C, an optional benign message ("is dit nog beschikbaar?" to a stranger's listing is normal use). Zero-activity accounts trip trust filters — *this is why the step is today.*
- ✅ **Done when:** 3 accounts verified and logged in on desktop + phone notes.
- 🆘 Phone verification blocks account #2/#3 → use one friend account + one of yours; only account A strictly must be new. Never buy accounts.

### 0.2 Sign the consent — ⏱ 10 min
`marketmind/kickoff/consent.txt` → print+sign+photo, **or** simpler: have the named reseller email you one line — *"I consent to being the named reseller user of MarketMind at Build Weekend 25–27 Sep 2026."* Save the thread (Art III accepts **written** consent). Fill their name/role + account-A handle on the consent form.
- ✅ **Done when:** signed form or consent email saved in `evidence/consent/`.
- 🆘 Nobody available → run `NAMED_RESELLER=unset` (Art III.3 — the UI shows "for named reseller unset"). **Never invent a person** (judge kiss-of-death list).

### 0.3 Freeze the hypotheses — ⏱ 10 min
Open `marketmind/kickoff/PREREGISTRATION.md` → fill the **frozen date + your name** at the top. H1/H2 wording may not change after this moment (Art IV). Take a timestamped screenshot — it's a Q&A flex ("pre-registered before any run").
- ✅ **Done when:** file filled + dated + screenshot in `evidence/`.

### 0.4 Get the repo onto your machine — ⏱ 10 min
1. Download `marketmind-build-weekend.bundle` from the workspace (single file, 177K).
2. `git clone marketmind-build-weekend.bundle marketmind && cd marketmind`
3. Push to GitHub: `gh repo create marketmind --private --source=. --push`  *(or: create an empty repo `knarayanareddy/marketmind` in the browser, then `git remote add origin git@github.com:knarayanareddy/marketmind.git && git push -u origin main`)*
4. Sanity: run the four proofs — **all must print PASS**:
```bash
python3 marketmind/skin/policy.py --eval marketmind/skin/gold.jsonl
python3 marketmind/app/run_walking_skeleton.py --selftest
python3 marketmind/app/tests/test_m1.py
python3 marketmind/app/tests/test_gate_parity.py    # needs node >= 18
```
- ✅ **Done when:** repo on GitHub + 4/4 PASS on your laptop.
- 🆘 No node on laptop → parity test is the only one needing it (`brew install node` / `nvm`); the other three run on bare Python.

---

## PHASE 1 — Friday 25 Sep — ~2.5 h spread over the day (D0: Rehearsal & Live Smoke)

### 1.1 Post the 5 listings — ⏱ 30 min (do this BEFORE buying credits)
Follow `marketmind/kickoff/LISTING-PLAN.md` exactly: Switch V2 **€150** · PS4 Slim **€120** · Canon EF-S 18-55 **€60** · game lot ×3 **€55** · Sony point-and-shoot **€45**. Real photos, honest condition text, correct category rubriek (*Games & Consoles* / *Fotografie*). For each: copy the **live URL** and listing id into a note (the own-listings actor + receipts evidence need them).
- ✅ **Done when:** 5 URLs saved in `evidence/listings.md`.
- 🆘 Fewer than 5 physical items → 2–3 is enough for the demo; the agent needs real inventory, not a warehouse.

### 1.2 Credits + keys — ⏱ 45–60 min (the money step; **start trials TODAY, not before**)
Work through `marketmind/WIRING.md` §1–5; the expanded version:

1. **Apify** (15 min) — https://www.apify.com → sign up (start the **free trial/credits now** so they're fresh through Sunday) → *Settings → API tokens* → `APFY_TOKEN`. Apify Store → search **"marktplaats"** (e.g. `haketa/marktplaats-scraper`) → note the actor id in `APIFY_ACTOR_LISTINGS`; also grab an eBay scraper (`apify/ebay-scraper`) for `APIFY_ACTOR_COMPS`. **Console test:** run the listing actor once with query `nintendo switch`, `maxItems=5` → items appear? Note the **run duration from the console** (a free pre-measurement of T05).
2. **n8n** (15 min) — if organizers hand out instances on Saturday, prefer that; otherwise start **n8n.cloud** trial now (https://app.n8n.cloud) and swap later. Record login URL.
3. **Telegram** (5 min) — in Telegram open **@BotFather** → `/newbot` → name e.g. `MarketMind <you>` → copy token → `TELEGRAM_BOT_TOKEN`. Send `/start` to your new bot. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser → grab `chat.id` → `TELEGRAM_CHAT_ID`.
4. **Optional now, fine later** — Airtable PAT + `receipts` table (columns in WIRING §4) — skipping is legal (jsonl degradation, Art VII.1). Browser-Use key → **skip tonight** (draft-assist is the M0 path). TF keys → if you still have 4prd credentials, probe and write `live|fallback` in a note; an OpenAI key only adds eval columns (a)/(b).
5. `cp app/env.example app/.env` → fill what you have. **NEVER commit `.env`** (already gitignored — verify with `git status`).
- ✅ **Done when:** `.env` has `APFY_TOKEN`, `APIFY_ACTOR_LISTINGS`, `TELEGRAM_*` filled.
- 🆘 Credits delayed → everything below works minus live data; Friday smoke becomes a labelled `--mode sim` rehearsal (Art VIII.3) and Saturday morning = activate+smoke before noon.

### 1.3 Import the n8n workflow — ⏱ 15 min
n8n → *Workflows → Import from file* → `marketmind/app/n8n/wf-m0-scan-decide.json` (start simple; `wf-m1-full.json` goes live Saturday). Wire credentials on the Apify HTTP node (Bearer = `APFY_TOKEN`) and the two Telegram nodes. **Leave the schedule toggle OFF.** Execute once manually on test data.
- ✅ **Done when:** manual execution completes and a receipt row/jsonl entry appears.

### 1.4 Fri evening, ~19:00–20:00 — THE LIVE SMOKE (30 min, `WIRING.md` §6)
Run in this order; stop and fix at the first failure (fallback ladder = `plan.md` §6):

| # | Command / action | What must happen | Note |
|---|---|---|---|
| 1 | `python3 app/run_walking_skeleton.py --mode live --only scan --measure` | Real listings print + a **cycle time** appears | **Write this number down** — it replaces `unmeasured` in the Sunday video |
| 2 | `python3 app/run_walking_skeleton.py --mode live` | Full loop → `app/out/receipts.jsonl` + `digest.txt` with honest states (`drafted` ≠ sent) | Read all 7-ish receipts — you're auditing your own agent |
| 3 | `python3 skin/policy.py --eval skin/gold.jsonl` | Still `PASS` (hostile→pursue = 0) | Nothing wired may break the oracle |
| 4 | Trigger the digest to Telegram (n8n manual or `mm/report.send_live`) | Message lands on your phone | Screenshot |
| 5 | Send **one real offer** to counterparty B via draft-assist — **your hand presses Send** (Art VII.2) | B receives it; reply optional | Log the outcome as an H1 datum if accepted |
| 6 | Copy screenshots + logs into `evidence/fri-smoke/` | Folder complete | Timestamps visible |

- ✅ **Done when:** all 6 rows ticked — one real scan, one real decision, one real message from your hand, one digest, one measured cycle time, evidence saved.
- 🆘 Platform blocks messaging → the **draft + human-Send** path *is* the fallback ladder's documented mode ("90% autonomous"); demo the navigation. Never fake a "sent".

---

## PHASE 2 — Saturday 26 Sep — event day (D1)

### 2.1 Pack & kickoff — ⏱ 30 min before leaving
Bag: laptop + charger · phone + cable · `app/.env` contents in your password manager (**not** in git) · the 5 listing URLs · this playbook · headphones (VO recording later). At kickoff: tell mentors **"the loop is tested — here are the receipts"** and take feedback as *config/parameter changes*, never a rebuild (the warden is watching). If organizers issue **their** Apify/n8n credits → swap the `.env` values and re-run the Fri smoke table (rows 1–4, 10 min).

### 2.2 Day build — priority order ("adapt on the day")
| Pri | Work | Done-when |
|---|---|---|
| **P0** | n8n `wf-m1-full.json` live: seen-ids node (run twice → second drops dupes), POLICY node pasted **from `policy_v1_node.js` or `policy_v0_node.js`** (mirror rule, Art II.4), Telegram draft/escalate, Airtable receipt | end-to-end manual execution green twice |
| **P0** | Schedule the Sunday 07:30 digest (or note "manual send Sun AM") | schedule visible |
| **P1** | `APIFY_ACTOR_OWN` on your 5 listings → T1 stale-reprice path (the Sony point-and-shoot is the demo candidate) | one `pursued_auto` receipt on your own item |
| **P1** | Inbound triage demo (`--inbound app/fixtures/inbound_sample.json` pattern on a real buyer message if one arrived) | dispute→T3 + "nog beschikbaar?"→draft shown |
| **P2** | Browser-Use session recording for beat 3 — **only if** P0/P1 green and it's before 18:00 | else use draft-assist screenshots (legal, common) |

Stop-the-line check at **13:00** and **18:00** (`plan.md` §6): if P0 isn't green at 13:00, freeze feature work and spend the afternoon on rehearsal + evidence prep. Gate v1 stays **flagged** (v0 default) — flip is allowed only after tonight's run proves the loop.

### 2.3 22:00 — ⭐ THE HERO OVERNIGHT (the single most important hour of the weekend: Run #2)
This run *is* the 25% "proven in real use" score and the "while you weren't watching" bonus. `checklists.md` §3, armed in this order:

1. **Config freeze** — commit or note "frozen 22:00". No edits during the run (bugs included — log them instead).
2. **Caps armed** — `MAX_COLD_OUTREACH=5`, 2 counter-rounds in code, `AUTO_PAUSE=0` — and **test `/pause` once before sleeping** (kill switch must work when you're not there).
3. **Counterparties briefed** — "the bot may message you tonight" (honest identity, Art III).
4. **Capture ON** — Apify run history · n8n executions · receipts jsonl/Airtable · Telegram thread · any session recordings.
5. **Write success criteria on paper before sleep:** ≥1 full notice→decide→act→report cycle · ≥1 refusal with reason · 1 receipt per decision · hostile→pursue = 0 · ≤5 cold offers.
6. **Watch window:** first 20 minutes live — touch nothing except the kill switch for genuine safety. Then **walk away and sleep.** The bonus requires it to be true.

- ✅ **Done when:** run armed, you're out of the loop, phone on for `/pause` emergencies only.

---

## PHASE 3 — Sunday 27 Sep — harvest → film → 15:00 (D2)

### 3.1 Morning harvest — 08:00–10:00
1. Assemble `evidence/hero-run/`: digest (forward to Saved Messages) · `receipts.jsonl` · n8n execution screenshots (timestamps!) · Apify runs screenshot (cycle times!) · Telegram thread · drafts folder.
2. Score the night against your written criteria. Compute **first-touch p50** from Apify timestamps → it replaces `unmeasured` on camera.
3. Feed the learning ledger: record H1 outcomes (offers sent / accepted / no-reply) → `app/out/state.json` priors or the eval-table ledger section. Run `python3 app/tests/eval_table.py` → fresh Art IV table for Q&A (columns (a)/(b) fill if keys exist now).
4. If — and only if — the night ran green on v0 and it's before 10:00: flip `--gate v1` for **one fresh morning pass** to capture v1 receipts. Never retro-fit v1 onto the night's history (Art VIII.3).

### 3.2 Film — 10:00–12:30 — the sheet is `marketmind/VIDEO-SHOTLIST.md`
Pre-roll captures first (its checklist), then record the 5 beats exactly as tabulated. Non-negotiables: **log on screen within 15s** · refusal is the wow · constraints line spoken verbatim (*"five cold offers a night, two counter-rounds, zero euros moved"*) · `drafted`-receipt visible · risk-tier + named reseller before 2:00 · **hard stop 2:00**. Record fallbacks before noon, labelled `REPLAY`. Watch once with sound off.
- ✅ **Done when:** exported video ≤ 2:00 + labelled fallbacks exist.

### 3.3 Submit — by **14:30** (deadline 15:00 — buffer, not heroics)
`checklists.md` §5: video uploaded · logs export linked · no keys/tokens in any frame · named reseller + risk-tier sentence present · numbers all traced (else `unmeasured`).

### 3.4 Live final — 16:15 (if top 10)
Pocket: `checklists.md` §7 (Q&A drill + red lines). Laptop open with the trump card **pre-typed**: `python3 marketmind/skin/policy.py --eval marketmind/skin/gold.jsonl` — run it live, say "9 fixtures, 0 hostile→pursue" after PASS. Open with the refusal story. The "over-engineered gate?" answer writes itself: *"the hero run ran on gate v0 — three rules."*

---

## Appendix A — time budget
| Phase | When | Total |
|---|---|---|
| 0 — accounts, consent, freeze, repo | Thu (or Fri AM) | ~45 min |
| 1 — listings, credits, smoke | Fri (evening block 19:00) | ~2.5 h |
| 2 — event build + hero run arming | Sat | on-site |
| 3 — harvest, film, submit | Sun 08:00–15:00 | ~5 h |

## Appendix B — the "never" list (kiss-of-death + constitution)
- Never commit `.env` · never invent numbers (`unmeasured` is legal) · never say "learns" without the ledger · never name unwired tech (JEV/TF/MLX without a `cache_hit` receipt) · never lead the video with "342 scanned" · never auto-message un-consented strangers beyond the 5/night cap · never let the agent move money · never score or report *persons* · never fake a "sent" that was "drafted" · never open the video with architecture.

## Appendix C — evidence folder (build it as you go)
```
evidence/
├── consent/            # signed form or consent email
├── listings.md         # the 5 URLs + ids
├── fri-smoke/          # Friday screenshots + cycle-time note
├── hero-run/           # Sunday harvest (the 25% proof)
└── eval/               # eval-table.md snapshots (Fri + Sun)
```
