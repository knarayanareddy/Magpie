#!/bin/bash
# magpiectl — zero-token phone controls for the Magpie loop (wired as Hermes quick_commands).
# Usage: magpiectl.sh pause|resume|status
# Kill-switch rule: NEVER print a success line unless the state change was verified on disk.
set -u -o pipefail
APP="$(cd "$(dirname "$0")/.." && pwd)"
PY=/usr/bin/python3
cd "$APP" || { echo "❌ Magpie: app dir not found"; exit 1; }

read_paused() {
  "$PY" -c 'import json,sys; print(json.load(open("out/state.json")).get("paused"))' 2>/dev/null
}

set_switch() {  # $1 = pause|resume, $2 = expected paused value (True|False)
  local out rc got
  out=$("$PY" run_walking_skeleton.py "--$1" 2>&1); rc=$?
  got=$(read_paused)
  if [ $rc -ne 0 ] || [ "$got" != "$2" ]; then
    echo "❌ Magpie $1 FAILED (exit $rc, state.json paused=${got:-unreadable}) — kill switch NOT confirmed."
    echo "${out}" | tail -3
    echo "Fallback: AUTO_PAUSE=1 in app/.env, or stop the loop process."
    return 1
  fi
  return 0
}

case "${1:-status}" in
  pause)  set_switch pause True || exit 1
          echo "⏸ Magpie paused (verified: state.json paused=True). Next item is observe-only; no new drafts." ;;
  resume) set_switch resume False || exit 1
          echo "▶️ Magpie resumed (verified: state.json paused=False). Acting again from the next item." ;;
  status) "$PY" - <<'EOF'
import json, subprocess
from pathlib import Path
out = Path("out")
h = json.loads((out / "daemon_health.json").read_text()) if (out / "daemon_health.json").exists() else {}
st = json.loads((out / "state.json").read_text()) if (out / "state.json").exists() else {}
pid = subprocess.run(["pgrep", "-f", "run_walking_skeleton.py.*--loop"], capture_output=True, text=True).stdout.split()
c = h.get("counts", {})
print(f"Magpie loop: {'RUNNING pid ' + pid[0] if pid else 'NOT RUNNING'} · status {h.get('status', '?')} · cycle {h.get('last_cycle', '?')} @ {h.get('last_ts', '?')}")
print(f"kill-switch: {'ON (observe-only)' if st.get('paused') else 'off'} · outreach today {st.get('outreach_count', 0)}")
print(f"last cycle: skipped {c.get('skipped', 0)} · escalated {c.get('escalated', 0)} · drafted {c.get('drafted', 0)} · auto {c.get('pursued_auto', 0)}")
EOF
  ;;
  *) echo "usage: magpiectl.sh pause|resume|status"; exit 2 ;;
esac
