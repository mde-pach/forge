#!/usr/bin/env bash
# Stop — the real gate. Blocks the turn from ending while the project is not green.
# Catches everything the per-edit hook cannot: cross-module type errors, tests,
# and files written through Bash rather than Edit.
set -uo pipefail
cd "${CLAUDE_PROJECT_DIR:-$PWD}" || exit 0
[ -f pyproject.toml ] || exit 0
# shellcheck source=/dev/null
. "${CLAUDE_PROJECT_DIR:-$PWD}/.claude/hooks/_guard.sh"

fail=""
run() { # name, command...
  local name="$1"; shift
  local out; out=$("$@" 2>&1); local rc=$?
  [ $rc -eq 0 ] || fail="${fail}
--- ${name} ---
${out}"
}

run "ruff format"  uv run --frozen ruff format --check .
run "ruff check"   uv run --frozen ruff check .
run "mypy (strict)" uv run --frozen mypy
[ -d tests ] && run "pytest" uv run --frozen pytest -q

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
