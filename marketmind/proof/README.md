# Magpie — Evidence Pack (redacted)

Built by `python3 marketmind/app/tools/build_proof.py` from the live runtime artefacts in `app/out/`
(gitignored). Re-run any time; `summary.json` carries a SHA-256 prefix of every file here.
**Redaction:** receipts are content-only by construction (Art III: no seller attributes); the pack exports
listing ids + decisions + scores only — no titles, descriptions, URLs, images, seller data, or tokens.

## What each file proves

| File | Proves | How to check |
|---|---|---|
| `summary.json` | live window, counts, **hostile→pursue = 0**, chain status, run/execution ids | read it |
| `receipts.redacted.jsonl` | every Python-loop decision, append-only, SHA-256 hash-chained (`prev_hash`→`row_hash`) | `python3 marketmind/app/run_walking_skeleton.py --selftest` verifies the chain algorithm; `summary.chain` is the verify result on the full log |
| `apify_runs.json` | real Apify runs behind the scans: `haketa/marktplaats-scraper` (listings) and `automation-lab/ebay-scraper` (comps) — run id, status, dataset id | look the run ids up in the Apify console |
| `comps_provenance.json` | per-family median/MAD, sample size `n`, **basis (sold/asking)**, source actor, fetch time | compare `n` and `source` with receipts' `margin_z` |
| `comps_sold_vs_asking.json` | the same 8 families priced both ways (Sat 12:50Z) — why the switch to sold prices mattered | read it |
| `n8n_executions.json` | **n8n Cloud production executions** of wf-m0 on live Apify data: per-node item counts, decisions, hash-chained in-workflow receipt ledger (continuous across executions), Telegram `message_id`s | execution id → n8n UI → *Executions* |

**n8n executions captured (workflow `2wmNJ9ZtWc0j516a`, trigger mode, one scheduled tick each):**
| exec | when (UTC) | comps basis | result |
|---|---|---|---|
| 1 | 12:40 | asking | 40 live listings → 3 drafted, 37 escalated; 4 Telegram messages (ids 104–107) |
| 2 | 12:55 | sold | 40 fetched → **0 after seen-ids dedupe** (all already decided in exec 1 — dedupe working as designed) |
| 3 | 13:00 | sold | seen-ids reset for the demo; ledger kept → chain continues from exec 1 head `9b4ea2e2…`; 40 decided, 0 drafted (cap/tier/no-margin), 1 summary message (id 120) |
| `telegram_messages.json` | Python-loop Telegram deliveries (`message_id` = Bot API delivery receipt) | logged from the moment id logging shipped (Sat 26 Sep afternoon) |
| `sell_receipts.redacted.jsonl` | **sell side (US-9)**: photo intake → human-confirmed identity → sold-comps price → listing draft → human post → buyer-message decisions → human approvals; own hash chain | only present once real items went through `sell.py` |

## Two paths, kept distinct
1. **Python loop** (`run_walking_skeleton.py --mode live --loop`) — the unattended hero-run engine:
   Apify scan → dedupe (ids + duplicate-photo dHash) → comps → gate v0 → draft/escalate/skip → receipt → Telegram.
2. **n8n Cloud workflow wf-m0** — the same decision path in n8n on live data (same gate, parity-tested;
   same live comps injected as `COMPS_JSON`), receipts in an in-workflow hash-chained ledger.
   It is **inactive by default** so the two engines never double-draft; executions in the pack were run
   deliberately (one production tick) to prove the n8n path.

## Comps basis — asking → sold (Sat 26 Sep, 12:50Z)
Until 12:50Z the comps were eBay DE **asking** prices (`automation-lab/ebay-scraper` has no sold filter).
They are now eBay.de **completed sales, last 30 days, used condition** (`caffein.dev/ebay-sold-listings`),
with defect/parts sales and successor models (Switch 2, Lite) excluded; a family with < 5 grounded sales
falls back to asking prices and is labelled `basis: asking`. The difference was large (Switch −45%,
AirPods −37%, Apple Watch +127%): **n8n execution 1 (asking basis) drafted 3 Switch offers that execution 3
(sold basis) correctly refused** as `no_margin` / `model_mismatch`. Receipts from before 12:50Z were decided on
asking prices — they are left unchanged (append-only), and this note is the correction.

## Honesty caveats (read before quoting any number)
- **Sold prices are gross.** Not yet netted out: shipping, platform fees, travel/collection, condition,
  resale time. Treat a draft as "worth a human look", not as proven margin.
- **Outreach is human-approved only.** Magpie drafts; a human presses Send (`--confirm` → `pursued_assisted`).
  No automatic seller message exists, by design (Art V, VII.2). Own-listing reprice (`edit_own_price`) is
  decided and receipted but not yet executed against Marktplaats.
- **Duplicate-photo match is a signal, not identity proof** — a match escalates for a human.
- n8n drafts are capped at `N8N_MAX_DRAFTS`/day (default 3) independently of the Python loop's cap.
- Notifier totals (morning summary) are per-process; a restart resets them.

## Offer maths (why a draft still leaves room)
`offer = min(round5(ask × 0.80), floor(ask × 0.80))` (H1 band, never < 40% of ask);
`margin_z = (comps_median − ask) / comps_MAD`, pursue only for `0 < margin_z ≤ 2.5`
(> 2.5 = too good to be true → escalate). The same listing on both bases:
- Nintendo Switch V2 (`m2443882388`), ask €125. **Asking basis** (exec 1, median €209.00, MAD €50.99, n=14):
  margin_z (209 − 125)/50.99 = 1.65 → drafted offer €100. **Sold basis** (exec 3, median €115.00, MAD €31.97,
  n=17 sales): margin_z (115 − 125)/31.97 = **−0.31 → escalate `no_margin`** — the seller already asks
  above what these consoles actually sell for. This is the refusal the sold basis exists to make.
- Genuine opportunity on the sold basis (exec 3): iPhone 14 (`Iphone 14 donker blauw`), ask €200 vs
  sold median €260 (MAD €49, n=16) → margin_z **1.22** → pursue-eligible; it escalated as `over_cap`
  only because n8n's daily draft cap (3) had been used by execution 1. Offer would be €160 → gross
  spread ≈ €100 vs sold median, before fees and shipping.
- Every draft message now carries its own calculation line (ask → offer · comps median/MAD/n/basis ·
  margin_z) in both the Python digest and the n8n Telegram draft.
