# Sourced by gate hooks. Prevents an infinite Stop-block loop without ever
# disabling the gate: after 3 identical consecutive failures it releases the
# turn ONCE, then re-arms (state reset) so the next turn blocks again.
_guard_state="${FORGE_PROJECT_DIR}/.claude/.gate-state"

# "Identical" has to mean identical to a human, not byte-identical: tool output
# carries build durations ("compiled in 197ms") and file counts that change on
# every run. Left raw, no two failures ever match, the counter never reaches 3
# and the gate deadlocks the session with no escape. Normalise away ANSI colour
# and every digit run before hashing.
guard_digest() {
  printf '%s' "$1" \
    | sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/[0-9][0-9]*/N/g' \
    | tr -s '[:space:]' ' ' \
    | cksum | cut -d' ' -f1
}

guard_should_release() {
  # In CI there is no human to unblock and no next turn to re-arm on: a release
  # would turn a red build green. The escape hatch exists for interactive loops
  # only.
  [ -n "${FORGE_GATE_NO_RELEASE:-}" ] && return 1
  local digest="$1" prev count
  prev=$(cut -d' ' -f1 "$_guard_state" 2>/dev/null || echo "")
  count=$(cut -d' ' -f2 "$_guard_state" 2>/dev/null || echo 0)
  case "$count" in ''|*[!0-9]*) count=0 ;; esac
  if [ "$prev" = "$digest" ]; then count=$((count + 1)); else count=1; fi
  if [ "$count" -ge 3 ]; then
    rm -f "$_guard_state"   # re-arm: the next turn is gated again
    return 0
  fi
  printf '%s %s\n' "$digest" "$count" > "$_guard_state" || return 1
  return 1
}
guard_clear() { rm -f "$_guard_state"; }
