#!/bin/bash
# Install Tailscale login autoconnect on this Mac.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BIN="${HOME}/.local/bin/tailscale-autoconnect.sh"
PLIST_SRC="${REPO_DIR}/configs/com.user.tailscale-autoconnect.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/com.user.tailscale-autoconnect.plist"
LABEL="com.user.tailscale-autoconnect"

mkdir -p "${HOME}/.local/bin" "${HOME}/.local/var/log" "${HOME}/Library/LaunchAgents"

install -m 755 "${REPO_DIR}/configs/tailscale-autoconnect.sh" "$BIN"
install -m 644 "$PLIST_SRC" "$PLIST_DST"

# Tailscale app setting: launch at login (GUI login item).
defaults write io.tailscale.ipn.macos TailscaleStartOnLogin -bool true

UID_NUM="$(id -u)"
launchctl bootout "gui/${UID_NUM}" "$PLIST_DST" 2>/dev/null || true
launchctl bootstrap "gui/${UID_NUM}" "$PLIST_DST"
launchctl enable "gui/${UID_NUM}/${LABEL}"
launchctl kickstart -k "gui/${UID_NUM}/${LABEL}"

echo "Installed ${LABEL}"
echo "TailscaleStartOnLogin=true"
echo ""
echo "For headless connect BEFORE user login, run once with sudo:"
echo "  sudo ${REPO_DIR}/configs/enable-tailscale-unattended.sh"
