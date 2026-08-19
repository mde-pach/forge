#!/usr/bin/env bash
# Expose a loopback service to your own devices, and to nothing else.
#
# Written generically on purpose: this is the reachability primitive for the
# whole stack, not just the dashboard. Anything you run on localhost - a dev
# server, a preview, a log viewer - reaches your phone the same way.
#
#   bash expose.sh                 # dashboard, port 7373
#   bash expose.sh 3000            # a dev server
#   bash expose.sh 3000 /preview   # mounted at a path
#   bash expose.sh --status
#   bash expose.sh --off [PORT]
#
# `tailscale serve` - never `tailscale funnel`. Serve reaches devices on your
# tailnet; Funnel publishes to the open internet. For session state that
# distinction is the entire security model, so Funnel is not an option this
# script offers.
set -euo pipefail

usage() { sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

command -v tailscale >/dev/null || {
  cat >&2 <<'MSG'
tailscale is not installed.
  macOS   brew install --cask tailscale        (or the App Store build)
  Linux   curl -fsSL https://tailscale.com/install.sh | sh
Then: sudo tailscale up
MSG
  exit 1
}

case "${1:-}" in
  --status)
    tailscale serve status
    exit 0 ;;
  --off)
    port="${2:-7373}"
    tailscale serve --https=443 --bg "http://127.0.0.1:${port}" off 2>/dev/null \
      || tailscale serve reset
    echo "stopped serving 127.0.0.1:${port}"
    exit 0 ;;
esac

port="${1:-7373}"
path="${2:-/}"

case "$port" in ''|*[!0-9]*) echo "expose: '$port' is not a port" >&2; exit 1 ;; esac

if ! tailscale status >/dev/null 2>&1; then
  echo "expose: tailscale is installed but not connected. Run: sudo tailscale up" >&2
  exit 1
fi

# The first run triggers a consent page to enable HTTPS certificates for the
# tailnet. That is a one-time click, and the command below is what prompts it.
if [ "$path" = "/" ]; then
  tailscale serve --bg "http://127.0.0.1:${port}"
else
  tailscale serve --bg --set-path "$path" "http://127.0.0.1:${port}"
fi

name=$(tailscale status --json 2>/dev/null \
        | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("Self",{}).get("DNSName","").rstrip("."))' 2>/dev/null || true)

echo
if [ -n "$name" ]; then
  echo "reachable from your devices at: https://${name}${path}"
else
  echo "reachable from your devices - run 'tailscale serve status' for the URL"
fi
cat <<'MSG'

Only devices signed in to your tailnet can reach it. Nothing is published to
the internet, no port is open on this machine, and there is no certificate to
renew.

On your phone: open the URL in Safari or Chrome and add it to the home screen.
It behaves like an app, and it is the same page whether the laptop is asleep or
not - it just shows the last state it managed to read.
MSG
