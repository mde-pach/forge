#!/usr/bin/env bash
# PostToolUse - runs on the single file Claude just edited. Fast only (~50ms).
# Cannot un-run the edit; exit 2 feeds the diagnostics back so Claude self-corrects.
# Decisions come from EXIT CODES, never from grepping tool output - output
# formats change between versions and a silently-passing gate is worse than none.
set -uo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
case "$file" in *.py) ;; *) exit 0 ;; esac
cd "${CLAUDE_PROJECT_DIR:-$PWD}" || exit 0
[ -f "$file" ] || exit 0

report=""
fmt_out=$(uv run --frozen ruff format --check "$file" 2>&1) || \
  report="${report}--- ruff format ---
${fmt_out}
"
lint_out=$(uv run --frozen ruff check "$file" 2>&1) || \
  report="${report}--- ruff check ---
${lint_out}
"

if [ -n "$report" ]; then
  printf 'ruff is not clean on %s. Fix before continuing:\n\n%s\nRun: uv run ruff format %s && uv run ruff check --fix %s\n' \
    "$file" "$report" "$file" "$file" >&2
  exit 2
fi
exit 0
