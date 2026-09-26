# Pre-registration — learning ledger (freeze at kickoff T04, before any run)

**Frozen:** Thu/Fri ______  ·  **By:** ______  ·  These hypotheses may not be rewritten after run #1 (Art IV: `unmeasured` legal, rewriting hypotheses after seeing data is not).

## Scope
- Niche (locked): **consoles & camera gear**. Categories `phones`, `bikes`, `ebikes` are **T3-only** (never auto).
- Market: NL (Marktplaats). Comps source: eBay sold (median/MAD).

## H1 — offer-band acceptance (buy side)
- **Claim:** offers at ≤ 80% of asking price in Games/Consoles are accepted at ≥ 25%.
- **Metric:** accepted / (accepted + rejected + no-reply after 48h), per offer band (≤75% / 75–85% / >85% of ask).
- **Falsified if:** acceptance < 25% in the ≤80% band after ≥ 5 observed outcomes in one category.
- **Ledger state after run #1:** `unmeasured` → updated run #2.

## H2 — bump timing (sell side)
- **Claim:** evening bumps (18:00–22:00) outperform morning bumps (08:00–10:00) on 24h view-count delta.
- **Metric:** median Δviews per bump, evening vs morning.
- **Falsified if:** morning ≥ evening after ≥ 3 bumps of each type.
- **Ledger state after run #1:** `unmeasured` → updated run #2.

## Kill-switch metric (build-breaking, Art IV.2)
- **hostile → pursue = 0** over `skin/gold.jsonl` (6 hostile of 9 fixtures). Above 0 fails the build.
