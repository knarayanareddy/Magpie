"""NOTIFY — event-driven Telegram for the autonomous loop (T08/T14).

The bot is shared with the Hermes gateway (same chat), so the loop must not spam:
  * loop armed / stopped            -> one line each
  * drafted > 0 in a cycle          -> the cycle digest (actionable: human presses Send)
  * feed errors                     -> only after ERR_STREAK consecutive failures, + one recovery line
  * kill-switch state change        -> one line
  * morning summary (MORNING_HOUR local, once per day) -> totals since last summary + last digest
Escalations/skips are NOT pushed per cycle — they're counted into the morning summary.
Send failures never crash the loop (logged, redacted — audit C4).
"""
from __future__ import annotations
import os, time
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo(os.environ.get("MM_TZ", "Europe/Amsterdam"))
except Exception:  # pragma: no cover
    TZ = None

ERR_STREAK = int(os.environ.get("NOTIFY_ERR_STREAK", "2"))
MORNING_HOUR = int(os.environ.get("NOTIFY_MORNING_HOUR", "8"))
STATES = ("skipped", "escalated", "drafted", "pursued_auto")


def enabled() -> bool:
    return (os.environ.get("NOTIFY_TELEGRAM", "1") == "1"
            and bool(os.environ.get("TELEGRAM_BOT_TOKEN")) and bool(os.environ.get("TELEGRAM_CHAT_ID")))


def _now() -> datetime:
    return datetime.now(TZ) if TZ else datetime.now()


class Notifier:
    def __init__(self, send="default", out_dir: Path | None = None):
        from . import report
        self._send = report.send_live if send == "default" else send  # None = record only (disabled/tests)
        self.out = out_dir
        self.err_streak = 0
        self.err_alerted = False
        self.paused = None
        self.totals = {s: 0 for s in STATES}
        self.mem = {"comps_hits": 0, "verdict_hits": 0, "cadence_skipped": 0, "cadence_fetched": 0}
        self.cycles = 0
        self.errors = 0
        self.last_morning = _now().date() if _now().hour >= MORNING_HOUR else None
        self.sent: list[str] = []  # for tests / log

    def _emit(self, text: str) -> None:
        text = text[:4000]
        self.sent.append(text)
        if self._send is None:
            return
        try:
            self._send(text)
        except Exception as e:  # never kill the loop over Telegram
            print(f"[notify] send failed: {e}")

    def armed(self, mode: str, gate: str, interval: int) -> None:
        self._emit(f"🐦 Magpie loop armed · mode={mode} gate={gate} every {interval}s · "
                   f"pings: drafts, errors, kill-switch, {MORNING_HOUR:02d}:00 summary · /magpie_pause to stop")

    def stopped(self, why: str) -> None:
        self._emit(f"🐦 Magpie loop stopped ({why}) after {self.cycles} cycles · "
                   + " · ".join(f"{k} {v}" for k, v in self.totals.items()))

    def cycle(self, summary: dict, digest_path: Path | None) -> None:
        self.cycles += 1
        counts = summary.get("counts", {})
        for s in STATES:
            self.totals[s] += int(counts.get(s, 0) or 0)
        for k in self.mem:                                   # US-10 market-memory savings, overnight totals
            self.mem[k] += int((summary.get("memory") or {}).get(k, 0) or 0)

        # errors: debounce transient feed hiccups
        if summary.get("error"):
            self.errors += 1
            self.err_streak += 1
            if self.err_streak >= ERR_STREAK and not self.err_alerted:
                self._emit(f"⚠️ Magpie feed failing {self.err_streak} cycles in a row: {summary['error'][:200]} "
                           f"· nothing acted while failing (fail-closed)")
                self.err_alerted = True
        else:
            if self.err_alerted:
                self._emit(f"✅ Magpie feed recovered after {self.err_streak} failed cycles")
            self.err_streak, self.err_alerted = 0, False

        # kill switch transitions
        p = bool(summary.get("paused"))
        if self.paused is not None and p != self.paused:
            self._emit("⏸ Magpie kill-switch ON — observe-only, no drafts" if p else "▶️ Magpie kill-switch off — acting again")
        self.paused = p

        # actionable: drafts awaiting a human
        if int(counts.get("drafted", 0) or 0) > 0 and digest_path and digest_path.exists():
            self._emit("📝 Draft awaiting you (drafted ≠ sent)\n" + digest_path.read_text()[:3500])

        self._maybe_morning(digest_path)

    def _maybe_morning(self, digest_path: Path | None) -> None:
        now = _now()
        if now.hour < MORNING_HOUR or self.last_morning == now.date():
            return
        self.last_morning = now.date()
        t = self.totals
        body = (f"☀️ Magpie overnight summary ({self.cycles} cycles, {self.errors} feed errors)\n"
                f"skipped {t['skipped']} · escalated {t['escalated']} · drafted {t['drafted']} · "
                f"auto {t['pursued_auto']}")
        m = self.mem
        if any(m.values()):
            import os
            usd = float(os.environ.get("APIFY_USD_PER_LISTINGS_RUN", "0.0196"))
            planned = m["cadence_skipped"] + m["cadence_fetched"]
            body += (f"\nmemory: {m['cadence_skipped']}/{planned} listing fetches skipped by learned cadence "
                     f"(≈${m['cadence_skipped'] * usd:.2f} Apify saved) · {m['comps_hits']} decisions on memory comps · "
                     f"{m['verdict_hits']} re-posts answered from verdict cache")
        if digest_path and digest_path.exists():
            body += "\n\nlast cycle:\n" + digest_path.read_text()[:3000]
        self._emit(body)
        self.totals = {s: 0 for s in STATES}
        self.mem = {k: 0 for k in self.mem}
        self.cycles = self.errors = 0
