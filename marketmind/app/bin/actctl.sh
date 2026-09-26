#!/bin/bash
# actctl — zero-token phone controls for the actuator (US-11; Hermes quick_commands take no arguments).
#   status  : session · budget · kill switch · pending approvals · last runs (read-only)
#   approve : ONE-TAP human approval of the OLDEST pending request (actor=human receipt). Does NOT execute —
#             execution stays a separate, explicit `act.py run <token>` on the Mac (dry-run unless ACT_LIVE=1).
set -u -o pipefail
APP="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP" || { echo "❌ act: app dir not found"; exit 1; }
case "${1:-status}" in
  status)  /usr/bin/python3 act.py status ;;
  approve) /usr/bin/python3 act.py approve oldest ;;
  *) echo "usage: actctl.sh status|approve"; exit 2 ;;
esac
