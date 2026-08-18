#!/usr/bin/env bash
# Stop - the real gate. Turbopack does NOT type-check, so `tsc --noEmit` is a
# separate mandatory step, and `next build` is what proves the app actually builds.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
. "$(dirname "${BASH_SOURCE[0]}")/_guard.sh"
cd "$FORGE_PROJECT_DIR" || exit 2

if [ ! -f package.json ]; then
  printf 'BLOCKED: no package.json at %s - the gate cannot verify this project.\n' "$FORGE_PROJECT_DIR" >&2
  exit 2
fi
if [ ! -d node_modules ]; then
  printf 'BLOCKED: node_modules missing - run `npm ci`. The gate is not running without it.\n' >&2
  exit 2
fi

export NO_COLOR=1
fail=""
run() {
  local name="$1"; shift
  local out; out=$("$@" 2>&1); local rc=$?
  [ $rc -eq 0 ] || fail="${fail}
--- ${name} ---
${out}"
}

run "biome ci"      ./node_modules/.bin/biome ci --colors=off .
run "tsc --noEmit"  ./node_modules/.bin/tsc --noEmit
run "next build"    npm run build --silent
grep -q '"test"' package.json && run "tests" npm test --silent

if [ -n "$fail" ]; then
  digest=$(guard_digest "$fail")
  if guard_should_release "$digest"; then
    printf '{"systemMessage":"Gate released after 3 identical failures to avoid a loop - the project is NOT green, and the gate re-arms on the next turn."}\n'
    exit 0
  fi
  printf 'The project gate is red. You are not done. Fix these, then finish:\n%s\n' "$fail" >&2
  exit 2
fi
guard_clear
exit 0
