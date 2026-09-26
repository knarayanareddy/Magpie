#!/bin/bash
# Magpie hero-run launcher (LaunchAgent target). caffeinate keeps the Mac awake for the loop's lifetime:
#   -i prevent idle sleep · -s prevent system sleep (on AC power) · -m keep disk awake.
# KeepAlive in the plist restarts this if the loop exits; the Python loop itself resumes from state.json.
set -u
APP="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP" || exit 1
echo "=== launchd start $(date -u +%Y-%m-%dT%H:%M:%SZ) pid $$ ==="
INTERVAL="${CYCLE_INTERVAL_S:-300}"
exec /usr/bin/caffeinate -i -s -m /usr/bin/python3 -u run_walking_skeleton.py --mode live --loop --interval "$INTERVAL"
