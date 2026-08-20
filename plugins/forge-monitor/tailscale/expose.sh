#!/usr/bin/env sh
# Make a loopback port reachable from your own devices, and from nothing else.
#
#   sh expose.sh on  PORT   -> prints the URL on stdout, nothing else
#   sh expose.sh off PORT
#
# Called only by `forge start`, which tears the mapping down again when you stop
# it. It prints the URL and nothing else on stdout because `forge start` reads
# that; everything human goes to stderr.
#
# `tailscale serve` - never `tailscale funnel`. Serve reaches devices signed in
# to your tailnet; Funnel publishes to the open internet. For session state that
# distinction is the whole security model, so Funnel is not an option this
# script offers.
#
# An earlier version took an optional mount path and a --status mode, on the
# theory that this was "the reachability primitive for the whole stack". Nothing
# ever called it that way. Speculative generality in a script nothing else uses
# is just more surface to keep correct.
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
  macOS   brew install --cask tailscale        (or the App Store build)
  Linux   curl -fsSL https://tailscale.com/install.sh | sh
Then: sudo tailscale up
MSG
  exit 1
}

tailscale status >/dev/null 2>&1 || {
  echo "tailscale is installed but not connected. Run: sudo tailscale up" >&2
  exit 1
}

# The first run triggers a one-time consent page enabling HTTPS certificates for
# the tailnet. This command is what prompts it.
tailscale serve --bg "http://127.0.0.1:${port}" >&2

name=$(tailscale status --json 2>/dev/null \
        | python3 -c 'import json,sys; print(json.load(sys.stdin).get("Self",{}).get("DNSName","").rstrip("."))' 2>/dev/null || true)

[ -n "$name" ] && printf 'https://%s/\n' "$name"
exit 0
