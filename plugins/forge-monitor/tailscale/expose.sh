#!/usr/bin/env sh
# expose.sh on|off PORT - serve a loopback port on the tailnet (never funnel).
# stdout: the URL, nothing else. Called only by `forge start`.
set -eu

mode="${1:-}"
port="${2:-7373}"

case "$port" in ''|*[!0-9]*) echo "expose: '$port' is not a port" >&2; exit 1 ;; esac

case "$mode" in
  off)
    tailscale serve --https=443 --bg "http://127.0.0.1:${port}" off >/dev/null 2>&1 \
      || tailscale serve reset >/dev/null 2>&1 || true
    exit 0 ;;
  on) ;;
  *) echo "usage: expose.sh on|off PORT" >&2; exit 1 ;;
esac

command -v tailscale >/dev/null 2>&1 || {
  cat >&2 <<'MSG'
tailscale is not installed.
  macOS   brew install --cask tailscale
  Linux   curl -fsSL https://tailscale.com/install.sh | sh
Then: sudo tailscale up
MSG
  exit 1
}

tailscale status >/dev/null 2>&1 || {
  echo "tailscale is installed but not connected. Run: sudo tailscale up" >&2
  exit 1
}

# First run prompts a one-time HTTPS consent page.
tailscale serve --bg "http://127.0.0.1:${port}" >&2

name=$(tailscale status --json 2>/dev/null \
        | python3 -c 'import json,sys; print(json.load(sys.stdin).get("Self",{}).get("DNSName","").rstrip("."))' 2>/dev/null || true)

[ -n "$name" ] && printf 'https://%s/\n' "$name"
exit 0
