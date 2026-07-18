#!/bin/bash
# Enable Tailscale unattended (headless) mode — connects before GUI login.
# Requires sudo. Run once on the agent server.
set -euo pipefail

TS="/Applications/Tailscale.app/Contents/MacOS/Tailscale"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

if [[ ! -x "$TS" ]]; then
  echo "Tailscale not found at $TS" >&2
  exit 1
fi

"$TS" set --unattended
echo "Unattended mode enabled."

"$TS" status --json | python3 -c "
import json, sys
d = json.load(sys.stdin).get('Self', {})
print('Unattended:', d.get('Unattended'))
print('Online:', d.get('Online'))
print('TailscaleIPs:', d.get('TailscaleIPs'))
"
