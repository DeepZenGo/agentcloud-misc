#!/bin/bash
# Ensure Tailscale is running and connected after login/boot.
# Installed by configs/install-tailscale-autostart.sh

set -euo pipefail

TS="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
LOG="${HOME}/.local/var/log/tailscale-autoconnect.log"

mkdir -p "$(dirname "$LOG")"

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG"
}

if [[ ! -x "$TS" ]]; then
  log "Tailscale CLI not found at $TS"
  exit 1
fi

log "tailscale autoconnect starting"

if ! pgrep -xq "Tailscale"; then
  log "opening Tailscale.app"
  open -ga Tailscale
  sleep 5
fi

for i in $(seq 1 60); do
  if ping -c 1 -t 2 1.1.1.1 &>/dev/null || ping -c 1 -t 2 8.8.8.8 &>/dev/null; then
    log "network reachable after ${i} attempt(s)"
    break
  fi
  sleep 2
done

for attempt in $(seq 1 10); do
  if "$TS" up >>"$LOG" 2>&1; then
    log "tailscale up succeeded"
    exit 0
  fi
  log "tailscale up attempt ${attempt} failed, retrying in 5s"
  sleep 5
done

log "tailscale up failed after retries"
exit 1
