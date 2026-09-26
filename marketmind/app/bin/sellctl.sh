#!/bin/bash
# sellctl — zero-token phone controls for the sell co-pilot (Hermes quick_commands take no arguments).
#   status  : pipeline + oldest pending draft (read-only)
#   approve : ONE-TAP approve the oldest pending reply draft; prints the text to paste into Marktplaats chat
# Exit status of sell.py is propagated; nothing is ever sent or posted by Magpie (drafted ≠ sent).
set -u -o pipefail
APP="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP" || { echo "❌ sell: app dir not found"; exit 1; }
case "${1:-status}" in
  status)  /usr/bin/python3 sell.py status --short ;;
  approve) /usr/bin/python3 sell.py approve ;;
  *) echo "usage: sellctl.sh status|approve"; exit 2 ;;
esac
