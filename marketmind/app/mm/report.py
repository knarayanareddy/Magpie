"""REPORT — Telegram digest v1 (design.md format). Refusal counts first-class (judge Mandate 2)."""
from __future__ import annotations
from . import config

FOOTER = ("Limited-risk decision support for a reseller's own actions. We judge listings, not people. "
          "We skip and escalate; we never spend, never bind a contract, never touch a third party's listing.")


def render(run_id: str, rows: list[dict], drafts: list[dict], timing: str,
           deduped: int = 0, paused: bool = False, learned: str = "unmeasured",
           outreach_used: int | None = None, error: str = "",
           cost_line: str = "", watchlist_info: str = "",
           triage_file: str = "") -> str:
    n = lambda s: sum(1 for r in rows if r["action_state"] == s)          # noqa: E731
    scanned = len(rows)
    refused = [r for r in rows if r["action_state"] in ("skipped", "escalated")][:3]
    used = n("drafted") if outreach_used is None else outreach_used  # audit C8: nightly counter, not per-run
    lines = [
        f"MarketMind — while you slept (for {config.RESELLER})  [{run_id}]",
    ]
    if error:  # honest failure digest — "no log" is never acceptable (Art VII.1)
        lines += [f"SCAN FAILED: {error}", "no decisions made tonight — nothing acted, nothing drafted.", FOOTER]
        return "\n".join(lines)
    lines += [
        f"scanned {scanned} · skipped {n('skipped')} · escalated {n('escalated')} · "
        f"acted {n('pursued_auto') + n('drafted')} (auto {n('pursued_auto')} / drafted {n('drafted')} awaiting you)",
        f"deduped {deduped} seen · kill-switch: {'ON (observe-only)' if paused else 'off'} · learned: {learned}",
    ]
    if cost_line:
        lines.append(cost_line)
    if watchlist_info:
        lines.append(watchlist_info)
    lines.append("refused first:" if refused else "refused first: (none this run)")
    for r in refused:
        word = "SKIP" if r["action_state"] == "skipped" else "ESC "
        lines.append(f"  {word} {r['listing_id']:22} {','.join(r['reason_codes'])}")
    if drafts:
        d = drafts[0]
        lines.append("acted:")
        lines.append(f"  DRAFT  {d['listing_id']:22} offer €{d['offer_eur']} "
                     f"({d['offer_ratio']*100:.0f}% of ask, round {d['counter_round']+1}/{d['max_counter_rounds']+1})")
    if scanned == 0:
        lines.append("empty feed — check APIFY_ACTOR_LISTINGS / quota (WIRING §1)")
    if n("escalated") > 0:
        tf = triage_file or "out/triage.html"
        lines.append(f"triage grid: {tf} ({n('escalated')} cards)")
    lines += [
        f"cold-outreach cap: {used}/{config.MAX_COLD_OUTREACH} used tonight",
        f"first-touch p50: {timing} · money moved: €0",
        # audit C3-honesty: only show controls that exist TODAY (/pause + human-Send drafts).
        # [approve]/[override] buttons appear with the T20 Telegram command handlers (WIRING §3).
        "controls: [/pause = kill switch] · drafts in out/drafts — you press Send (Art VII.2)",
        FOOTER,
    ]
    return "\n".join(lines)


def send_live(text: str) -> None:
    import json, os, urllib.request
    token, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
    body = json.dumps({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=30)
    except Exception as e:
        # never leak the token-bearing path in a traceback (audit C4)
        raise RuntimeError(f"telegram send failed: {type(e).__name__} (details redacted)") from None
