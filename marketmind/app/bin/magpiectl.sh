#!/bin/bash
# magpiectl — zero-token phone controls for the Magpie loop (wired as Hermes quick_commands).
# Usage: magpiectl.sh pause|resume|status
set -u
APP="$(cd "$(dirname "$0")/.." && pwd)"
PY=/usr/bin/python3
cd "$APP" || exit 1
case "${1:-status}" in
  pause)  "$PY" run_walking_skeleton.py --pause  2>&1 | tail -1
          echo "Magpie: new drafts blocked from the next cycle (receipts keep flowing, observe-only)." ;;
  resume) "$PY" run_walking_skeleton.py --resume 2>&1 | tail -1
          echo "Magpie: acting again from the next cycle." ;;
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
