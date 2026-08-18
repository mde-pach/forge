#!/usr/bin/env bash
# Stop - the real gate. Turbopack does NOT type-check, so `tsc --noEmit` is a
# separate, mandatory step; without it type errors reach production.
set -uo pipefail
cd "${CLAUDE_PROJECT_DIR:-$PWD}" || exit 0
[ -f package.json ] || exit 0
# shellcheck source=/dev/null
. "${CLAUDE_PROJECT_DIR:-$PWD}/.claude/hooks/_guard.sh"

fail=""
run() {
  local name="$1"; shift
  local out; out=$("$@" 2>&1); local rc=$?
  [ $rc -eq 0 ] || fail="${fail}
--- ${name} ---
${out}"
}

run "biome ci"      npx --no-install biome ci .
run "tsc --noEmit"  npx --no-install tsc --noEmit
grep -q '"test"' package.json && run "tests" npm test --silent

if [ -n "$fail" ]; then
  digest=$(printf '%s' "$fail" | cksum | cut -d' ' -f1)
  if guard_should_release "$digest"; then
    printf '{"systemMessage":"Gate still failing after 3 identical attempts - released to avoid a loop. The project is NOT green."}\n'
    exit 0
  fi
  printf 'The project gate is red. You are not done. Fix these, then finish:\n%s\n' "$fail" >&2
  exit 2
fi
guard_clear
exit 0
