#!/usr/bin/env bash
# PostToolUse - runs on the single file Claude just edited. Fast only.
# Biome does format + lint + import sorting in one pass, no TS compiler needed.
# Decisions come from EXIT CODES, never from grepping tool output.
# NOTE: the local binary is invoked directly. `npx biome` resolves to an
# unrelated squatted package (`biome@0.3.3`); the real one is @biomejs/biome.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_jq

file=$(jq -r '.tool_input.file_path // empty')
case "$file" in *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.json|*.jsonc|*.css) ;; *) exit 0 ;; esac
cd "$FORGE_PROJECT_DIR" || exit 2
[ -f "$file" ] || exit 0

BIOME="./node_modules/.bin/biome"
if [ ! -x "$BIOME" ]; then
  printf 'BLOCKED: %s not found - run `bun install`. The gate is not running without it.\n' "$BIOME" >&2
  exit 2
fi

# NO_COLOR is not honoured by biome; --colors=off is. Without it the hook
# feeds Claude kilobytes of ANSI escapes instead of a readable diagnostic.
if ! out=$("$BIOME" check --colors=off "$file" 2>&1); then
  printf 'biome is not clean on %s. Fix before continuing:\n\n%s\n\nRun: ./node_modules/.bin/biome check --write %s\n' \
    "$file" "$out" "$file" >&2
  exit 2
fi
exit 0
