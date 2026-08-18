# Sourced by gate hooks. Prevents an infinite Stop-block loop: if the gate
# fails with the identical output 3 times running, it lets the turn end with a
# loud warning instead of trapping the session.
_guard_state="${CLAUDE_PROJECT_DIR:-$PWD}/.claude/.gate-state"
guard_should_release() {
  local digest="$1" prev count
  prev=$(cut -d' ' -f1 "$_guard_state" 2>/dev/null || echo "")
  count=$(cut -d' ' -f2 "$_guard_state" 2>/dev/null || echo 0)
  case "$prev" in "$digest") count=$((count + 1)) ;; *) count=1 ;; esac
  printf '%s %s\n' "$digest" "$count" > "$_guard_state"
  [ "$count" -ge 3 ]
}
guard_clear() { rm -f "$_guard_state"; }
