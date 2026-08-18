#!/usr/bin/env bash
# PostToolUse - runs on the single file Claude just edited. Fast only.
# Biome does format + lint + import sorting in one pass, no TS compiler needed.
# Decisions come from EXIT CODES, never from grepping tool output - output
# formats change between versions and a silently-passing gate is worse than none.
set -uo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
case "$file" in *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.json|*.jsonc|*.css) ;; *) exit 0 ;; esac
cd "${CLAUDE_PROJECT_DIR:-$PWD}" || exit 0
[ -f "$file" ] || exit 0

if ! out=$(npx --no-install biome check "$file" 2>&1); then
  printf 'biome is not clean on %s. Fix before continuing:\n\n%s\n\nRun: npx biome check --write %s\n' \
    "$file" "$out" "$file" >&2
  exit 2
fi
exit 0
