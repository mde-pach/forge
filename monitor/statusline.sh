#!/usr/bin/env bash
# forge-monitor statusline — a per-turn heartbeat that costs zero context.
#
# Claude Code pipes a rich JSON object into the statusline script every turn:
# session id and name, cwd, model, cost, context-window usage, rate limits, git
# worktree and PR state. That output is chrome rendered for the HUMAN - it is
# never part of the model's context - which makes it the highest-bandwidth
# observation point in the system that the session cannot see.
#
# So this does two jobs: it appends the heartbeat for the collector, and it
# prints the line you actually want in your terminal.
set -uo pipefail

payload=$(timeout 2 cat 2>/dev/null || echo '{}')
state_dir="${FORGE_MONITOR_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/forge-monitor}"

{
  mkdir -p "$state_dir" 2>/dev/null || true
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$payload" | timeout 2 jq -c \
      --arg ev "Heartbeat" \
      --arg at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      --arg host "$(hostname 2>/dev/null || echo unknown)" \
      '{forge_event:$ev, at:$at, host:$host,
        session_id:.session_id, cwd:.cwd,
        name:.session_name, model:.model.display_name,
        cost_usd:.cost.total_cost_usd,
        lines_added:.cost.total_lines_added,
        lines_removed:.cost.total_lines_removed,
        context_pct:.context_window.used_percentage,
        branch:.workspace.git_worktree, pr:.pr.number}' \
      >> "$state_dir/events.ndjson" 2>/dev/null || true
  fi
} >/dev/null 2>&1

# --- the visible part ---
if command -v jq >/dev/null 2>&1; then
  # IFS=tab is load-bearing: model display names contain spaces ("Opus 5"), so
  # default word-splitting shifts every field left and the cost prints as the
  # context percentage. Caught by running it, not by reading it.
  IFS=$'\t' read -r dir model pct cost <<<"$(printf '%s' "$payload" | jq -r '
    [ (.workspace.current_dir // .cwd // "" | split("/") | last // "?"),
      (.model.display_name // "?"),
      (.context_window.used_percentage // 0 | floor),
      (.cost.total_cost_usd // 0) ] | @tsv' 2>/dev/null)"
  printf '%s \xc2\xb7 %s \xc2\xb7 ctx %s%% \xc2\xb7 $%s\n' \
    "${dir:-?}" "${model:-?}" "${pct:-0}" "${cost:-0}"
else
  printf 'forge\n'
fi
exit 0
