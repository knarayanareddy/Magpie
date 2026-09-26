#!/bin/bash
# magpie-supervise — keep the Magpie loop alive for the hero run (launchd alternative).
# Why not launchd: the repo lives in ~/Downloads, which macOS TCC blocks for launchd-spawned
# processes ("Operation not permitted", exit 126) unless /bin/bash + python get Full Disk Access.
# This supervisor is started from a terminal that already has access, in its own session (no SIGHUP).
#   start | stop | status
# Behaviour: respawn the loop on any exit except a requested stop; backoff 30s→300s on crash loops;
# caffeinate -i -s -m -w <loop pid> keeps the Mac awake exactly as long as the loop lives
# (-s only holds on AC power; the lid must stay open).
# Stop is PID-exact (pid files), never pattern-kill: SIGTERM to the python loop (trapped => clean 'stopped' ping).
set -u
APP="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$APP/out"
SUP_PID="$OUT/supervisor.pid"
LOOP_PID="$OUT/loop.pid"
STOPF="$OUT/supervisor.stop"
LOG="$OUT/daemon.log"
PY=/usr/bin/python3

alive() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

run_forever() {
  echo $$ > "$SUP_PID"
  rm -f "$STOPF"
  local backoff=30
  trap 'touch "$STOPF"' INT TERM          # stop is driven by the flag + PID-exact kill in `stop`
  while [ ! -f "$STOPF" ]; do
    echo "=== supervisor $(ts) starting loop (supervisor pid $$) ===" >> "$LOG"
    local t0; t0=$(date +%s)
    "$PY" -u "$APP/run_walking_skeleton.py" --mode live --loop --interval "${CYCLE_INTERVAL_S:-300}" >> "$LOG" 2>&1 &
    local lp=$!
    echo "$lp" > "$LOOP_PID"
    /usr/bin/caffeinate -i -s -m -w "$lp" &      # exits by itself when the loop exits
    while kill -0 "$lp" 2>/dev/null; do sleep 2; done
    wait "$lp" 2>/dev/null; local rc=$?
    rm -f "$LOOP_PID"
    [ -f "$STOPF" ] && break
    local ran=$(( $(date +%s) - t0 ))
    [ "$ran" -gt 600 ] && backoff=30
    echo "=== supervisor $(ts) loop exited rc=$rc after ${ran}s; respawn in ${backoff}s ===" >> "$LOG"
    local w=0; while [ "$w" -lt "$backoff" ] && [ ! -f "$STOPF" ]; do sleep 1; w=$((w + 1)); done
    backoff=$(( backoff * 2 > 300 ? 300 : backoff * 2 ))
  done
  echo "=== supervisor $(ts) stopped on request ===" >> "$LOG"
  rm -f "$SUP_PID"
}

case "${1:-status}" in
  start)
    if alive "$SUP_PID"; then echo "supervisor already running (pid $(cat "$SUP_PID"))"; exit 0; fi
    stray=$(pgrep -f "Python -u $APP/run_walking_skeleton.py|python3 -u run_walking_skeleton.py" | tr '\n' ' ')
    if [ -n "$stray" ]; then echo "❌ refusing to start: unsupervised loop running (pids $stray) — stop it first"; exit 1; fi
    "$PY" -c 'import os,sys; os.setsid(); os.execv("/bin/bash", ["/bin/bash", sys.argv[1], "_run"])' \
        "$0" </dev/null >/dev/null 2>&1 &
    for _ in 1 2 3 4 5; do sleep 1; alive "$LOOP_PID" && break; done
    if alive "$SUP_PID" && alive "$LOOP_PID"; then
      echo "supervisor started (pid $(cat "$SUP_PID")) · loop pid $(cat "$LOOP_PID")"
    else echo "❌ supervisor failed to start"; exit 1; fi ;;
  _run) run_forever ;;
  stop)
    alive "$SUP_PID" || alive "$LOOP_PID" || { echo "supervisor not running"; rm -f "$SUP_PID" "$LOOP_PID"; exit 0; }
    touch "$STOPF"
    alive "$LOOP_PID" && kill -TERM "$(cat "$LOOP_PID")"         # loop traps TERM => clean 'stopped' ping
    for _ in $(seq 1 15); do sleep 1; alive "$SUP_PID" || alive "$LOOP_PID" || break; done
    if alive "$SUP_PID" || alive "$LOOP_PID"; then
      echo "❌ stop NOT confirmed (supervisor $(alive "$SUP_PID" && cat "$SUP_PID" || echo -), loop $(alive "$LOOP_PID" && cat "$LOOP_PID" || echo -))"
      exit 1
    fi
    rm -f "$SUP_PID" "$LOOP_PID"
    echo "supervisor + loop stopped (verified by pid)" ;;
  status)
    if alive "$SUP_PID"; then echo "supervisor RUNNING pid $(cat "$SUP_PID")"; else echo "supervisor NOT running"; fi
    if alive "$LOOP_PID"; then echo "loop RUNNING pid $(cat "$LOOP_PID")"; else echo "loop NOT running"; fi
    pmset -g assertions | grep -q 'caffeinate' && echo "caffeinate: holding sleep assertion" || echo "caffeinate: none"
    pmset -g batt | sed -n 1p ;;
  *) echo "usage: $0 start|stop|status"; exit 2 ;;
esac
