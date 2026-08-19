#!/usr/bin/env bash
# forge-monitor event emitter.
#
# THE CONTRACT OF THIS SCRIPT, in order of importance:
#
#   1. It writes NOTHING to stdout, ever. Claude Code shows a hook's stdout to
#      the model on exactly three events (SessionStart, UserPromptSubmit,
#      UserPromptExpansion) and sends it to the debug log on all the others.
#      Printing nothing means the session cannot observe this layer on any
#      event, including those three. The monitor watches the session; the
#      session never learns it is watched.
#
#   2. It always exits 0. Exit 2 is a blocking error on several events - a
#      monitor that can stop a turn is a monitor that will eventually stop a
#      turn at the worst moment. Every failure path here is swallowed.
#
#   3. It is local and fast. It appends one line to a file. It never opens a
#      network connection, never resolves a name, never touches a credential.
#      Publishing is the collector's job, in another process, with its own
#      identity.
#
# Usage (from ~/.claude/settings.json, never from a project's .claude/):
#   bash <path>/emit.sh <event-name>

event="${1:-unknown}"
state_dir="${FORGE_MONITOR_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/forge-monitor}"
log="$state_dir/events.ndjson"

{
  mkdir -p "$state_dir" 2>/dev/null || exit 0

  payload=$(timeout 2 cat 2>/dev/null || true)
  [ -n "$payload" ] || payload='{}'

  # One NDJSON line: our envelope plus the runtime's payload, verbatim.
  # jq is not assumed - the hook must work on a machine that lacks it, because
  # failing closed is correct for a GATE and catastrophic for a MONITOR.
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$payload" | timeout 2 jq -c \
      --arg ev "$event" \
      --arg at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      --arg host "$(hostname 2>/dev/null || echo unknown)" \
      '{forge_event:$ev, at:$at, host:$host} + .' >> "$log" 2>/dev/null || true
  else
    printf '{"forge_event":"%s","at":"%s","host":"%s","raw":%s}\n' \
      "$event" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(hostname 2>/dev/null || echo unknown)" \
      "$(printf '%s' "$payload" | tr -d '\n')" >> "$log" 2>/dev/null || true
  fi

  # Cheap rotation. An unbounded log on a laptop is a bug that shows up in a
  # month, in the form of a full disk, at the worst possible moment.
  if [ -f "$log" ]; then
    size=$(wc -c < "$log" 2>/dev/null || echo 0)
    if [ "${size:-0}" -gt 10000000 ]; then
      mv -f "$log" "$log.1" 2>/dev/null || true
    fi
  fi
} >/dev/null 2>&1

exit 0
