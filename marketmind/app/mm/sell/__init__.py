"""SELL side (US-9): photo dump -> priced listing drafts + negotiation co-pilot. You approve with one tap.

Isolation contract (so the buy-side hero loop is never disturbed):
  * own state      out/sell/state.json      (never touches out/state.json)
  * own receipts   out/sell/receipts.jsonl  (own hash chain, same algorithm as mm/receipts.py)
  * own photos     out/sell/photos/         (sanitized re-encodes only; originals never copied)
  * reuses mm.receipts / mm.phash / mm.jev / mm.notice / skin.policy READ-ONLY — no edits there.
Constitution: models propose, code decides (Art V); drafted != posted/sent (Art VII.2); max 2 counter-rounds;
no money, no shipping labels, pickup via platform flow (Art V.3); no buyer profiling (Art III).
"""
