#!/bin/bash
# memory-sync — sidecar that keeps out/market.db current from EXISTING Apify run datasets (reads only,
# never starts a scrape). Independent of the hero loop: separate process, separate PID file; the loop
# never reads or writes market.db tonight (US-10 rollout: overnight run = untouched "before" baseline).
#   start | stop | status      (interval: MEM_SYNC_INTERVAL_S, default 1800)
# macOS has no setsid(1): detach via python os.setsid() like magpie-supervise.sh.
set -u -o pipefail
APP="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$APP/out"; PIDF="$OUT/memory_sync.pid"; LOG="$OUT/memory_sync.log"
INTERVAL="${MEM_SYNC_INTERVAL_S:-1800}"
PY=/usr/bin/python3
alive() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }

case "${1:-status}" in
  _run)
    echo $$ > "$PIDF"
    trap 'rm -f "$PIDF"; exit 0' TERM INT
    while true; do
      echo "=== $(date -u +%FT%TZ) sync" >> "$LOG"
      "$PY" "$APP/tools/backfill_memory.py" --quiet >> "$LOG" 2>&1 || echo "sync failed (will retry)" >> "$LOG"
      "$PY" "$APP/tools/memory_metrics.py" > /dev/null 2>> "$LOG" || true
      sleep "$INTERVAL" & wait $!
    done ;;
  start)
    if alive "$PIDF"; then echo "memory-sync already RUNNING pid $(cat "$PIDF")"; exit 0; fi
    "$PY" -c 'import os,sys; os.setsid(); os.execv("/bin/bash", ["/bin/bash", sys.argv[1], "_run"])' \
      "$0" < /dev/null > /dev/null 2>&1 &
    sleep 2
    if alive "$PIDF"; then echo "memory-sync RUNNING pid $(cat "$PIDF") · every ${INTERVAL}s · log out/memory_sync.log"
    else echo "❌ memory-sync failed to start (see $LOG)"; exit 1; fi ;;
  stop)
    if alive "$PIDF"; then kill -TERM "$(cat "$PIDF")"; sleep 1
      alive "$PIDF" && { echo "❌ still running"; exit 1; }; echo "memory-sync stopped"
    else rm -f "$PIDF"; echo "memory-sync not running"; fi ;;
  status)
    if alive "$PIDF"; then echo "memory-sync RUNNING pid $(cat "$PIDF")"; else echo "memory-sync STOPPED"; fi
    tail -2 "$LOG" 2>/dev/null ;;
  *) echo "usage: memory-sync.sh start|stop|status"; exit 2 ;;
esac
