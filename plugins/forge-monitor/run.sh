#!/usr/bin/env bash
# Start everything the monitor needs on this machine: the collector loop and
# the dashboard server. Both are plain user processes - no root, no systemd
# unit required, no port open to anything but loopback.
#
#   bash run.sh              # foreground, both processes
#   bash run.sh --collector  # just the collector
#   bash run.sh --dashboard  # just the dashboard
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${FORGE_MONITOR_PORT:-7373}"

start_collector() { python3 "$HERE/collector.py" --watch & }
start_dashboard() { python3 "$HERE/serve.py" --port "$PORT" & }

case "${1:-both}" in
  --collector) start_collector ;;
  --dashboard) start_dashboard ;;
  both) start_collector; start_dashboard ;;
  *) echo "usage: run.sh [--collector|--dashboard]" >&2; exit 1 ;;
esac

trap 'kill 0' EXIT INT TERM
wait
