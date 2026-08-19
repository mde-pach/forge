#!/usr/bin/env bash
# forge-monitor event emitter.
#
# Registered with `async: true`, so Claude Code does not wait for it. That is
# what lets a hook publish over the network without ever being on the critical
# path of a turn - and it is why there is no daemon: the session keeps its own
# record current, and nothing has to be running for the state to be true.
#
# THE CONTRACT, in order of importance:
#
#   1. It writes NOTHING to stdout, ever. Claude Code shows a hook's stdout to
#      the model on exactly three events (SessionStart, UserPromptSubmit,
#      UserPromptExpansion) and sends it to the debug log on the rest. Printing
#      nothing means the session cannot observe this layer on ANY event.
#
#   2. It always exits 0. Exit 2 is a blocking error on several events. A gate
#      must fail closed; a monitor must fail open, because a monitor that can
#      stop a turn eventually will, at the worst possible moment.
#
#   3. It never publishes more than it must. Every event updates the local
#      record; only events that change what a human would want to know cause a
#      push, and non-urgent ones are rate-limited. Attention never waits.
#
#   bash "${CLAUDE_PLUGIN_ROOT}/hooks/emit.sh" <event-name>

event="${1:-unknown}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="${FORGE_MONITOR_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/forge-monitor}"

{
  mkdir -p "$STATE" 2>/dev/null || exit 0
  payload=$(timeout 2 cat 2>/dev/null || true)
  [ -n "$payload" ] || payload='{}'

  # Raw log: the audit trail, and the fixture source when we finally test this
  # against a real session.
  printf '%s\n' "$payload" >> "$STATE/events-${event}.ndjson" 2>/dev/null || true

  command -v python3 >/dev/null 2>&1 || exit 0

  decision=$(printf '%s' "$payload" | timeout 10 python3 "$HERE/record.py" "$event" 2>/dev/null || echo hold)
  sid=$(printf '%s' "$payload" | timeout 5 python3 -c \
        'import json,sys;print((json.load(sys.stdin) or {}).get("session_id") or "")' 2>/dev/null || true)

  # A session starting is the moment to repair what nobody was watching: a
  # laptop that closed mid-session fires no SessionEnd, so its record would
  # claim to be running forever.
  if [ "$event" = "SessionStart" ]; then
    timeout 20 python3 "$HERE/sweep.py" "$sid" >/dev/null 2>&1 || true
  fi

  if [ "$decision" = "publish" ] && [ -n "$sid" ]; then
    timeout 60 bash "$HERE/publish.sh" "$sid" >/dev/null 2>&1 || true
  fi

  # Bound the raw logs. An unbounded file on a laptop is a bug that arrives in
  # a month as a full disk, at the worst moment.
  for f in "$STATE"/events-*.ndjson; do
    [ -f "$f" ] || continue
    sz=$(wc -c < "$f" 2>/dev/null || echo 0)
    [ "${sz:-0}" -gt 5000000 ] && mv -f "$f" "$f.1" 2>/dev/null
  done
} >/dev/null 2>&1

exit 0
