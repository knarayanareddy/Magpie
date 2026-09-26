#!/bin/bash
# Install/uninstall the Magpie loop LaunchAgent.  Usage: install-launchd.sh [install|uninstall|status]
# ⚠ KNOWN LIMITATION (verified Sat 26 Sep): with the repo under ~/Downloads, macOS TCC blocks
# launchd-spawned bash ("Operation not permitted", exit 126). Either move the repo outside
# ~/Downloads|~/Documents|~/Desktop, or grant /bin/bash Full Disk Access. Until then use
# bin/magpie-supervise.sh (same restart + caffeinate behaviour, started from a permitted terminal).
set -u -o pipefail
APP="$(cd "$(dirname "$0")/.." && pwd)"
DST="$HOME/Library/LaunchAgents/com.magpie.loop.plist"
DOMAIN="gui/$(id -u)"
case "${1:-install}" in
  install)
    # refuse to double-run: stop any hand-started loop first (SIGINT => clean 'stopped' notification)
    if pgrep -f 'run_walking_skeleton.py.*--loop' >/dev/null && ! launchctl print "$DOMAIN/com.magpie.loop" >/dev/null 2>&1; then
      echo "stopping hand-started loop: $(pgrep -f 'run_walking_skeleton.py.*--loop' | tr '\n' ' ')"
      pkill -INT -f 'run_walking_skeleton.py.*--loop'; sleep 3
    fi
    chmod +x "$APP/bin/magpie-loop.sh"
    sed "s#__APP__#$APP#g" "$APP/bin/com.magpie.loop.plist" > "$DST"
    plutil -lint "$DST" || exit 1
    launchctl bootout "$DOMAIN/com.magpie.loop" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$DST" && echo "installed + started: com.magpie.loop" ;;
  uninstall)
    launchctl bootout "$DOMAIN/com.magpie.loop" 2>/dev/null && echo "stopped com.magpie.loop"
    rm -f "$DST" ;;
  status)
    launchctl print "$DOMAIN/com.magpie.loop" 2>/dev/null | grep -E 'state =|pid =|runs =|last exit' || echo "not loaded" ;;
esac
