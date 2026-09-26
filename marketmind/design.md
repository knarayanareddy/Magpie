# MarketMind — Design & Format Lockfile (Art XIII full model)

Any web surface (receipt card, eval table, optional dashboard), the Telegram digest, and the video's on-screen UI obey this file. Change this file first to deviate.

## Tokens

- Paper `#F3EFE7` · Ink `#1C1915` · Rule `#C9C2B4` · one accent only: brick `#8C3A2B` (for SKIP/ESCALATE words)
- IBM Plex Sans (UI) + IBM Plex Mono (numbers, ids, hashes). No Inter. No system-default-as-unchosen.
- Radius 2px. No box-shadow. No gradients/glass/glow. Motion: none. Emoji are not icons.
- **Banned motifs:** purple/indigo/violet/fuchsia, sparkle/shield logos, "powered by AI", three feature cards, marketing hero sections. This is an operator instrument.

## Status words (colour is never the only channel)

| State | Word | Notes |
|---|---|---|
| decision | **PURSUE** / **ESCALATE** / **SKIP** | uppercase word + colour |
| action_state | `pursued_auto` / `pursued_assisted` / `escalated` / `skipped` | never blurred; `drafted ≠ sent` (Art VII.2) |
| degraded | `judge=unconfigured` / `grounding=stale` / `unmeasured` | honest values, printed as-is (Art IV.3) |

## Receipt card (one decision, one card)

Thumb 96×96 if image · title 16/600 · price mono · description truncated to 4 lines **as plain text** (injection strings stay **visible** — Art XIII.3) · bucket chip (mono, paper fill, rule border) · status word · reason codes mono · receipt id + hash footer link · `actor` row when overridden.

## Telegram digest (morning report)

```
MarketMind — while you slept (for NAMED_RESELLER)
scanned 342 · skipped 29 · escalated 6 · acted 5 (auto 3 / assisted 2)
refused first:
  SKIP  mm-inject-01  injection_or_jailbreak   (string shown)
  ESC   iPhone 14     price_too_good (z=4.1)
acted:
  ASSIST  Switch V2  offer €120 (cap 5/night: 2 used)
learned: priors ▸ Games accept-rate 2/5 → 3/7  (H1 pending)
first-touch p50: 6 min (measured) · money moved: €0
[approve] [override→escalate] [/pause]
```
Rules: ≤25 lines · numbers mono · skip/escalate counts first-class (not buried) · caps remaining shown · named human + risk-tier sentence in footer of every surface:

> Limited-risk decision support for a reseller's own actions. We judge listings, not people. We skip and escalate; we never spend, never bind a contract, never touch a third party's listing.

## Video chrome

On-screen receipts use the card design above. Fallback/replay segments are **labelled** `REPLAY — run #2, 03:12` (Art VIII.3). No fake cursors, no mockups standing in for real surfaces.
