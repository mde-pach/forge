#!/usr/bin/env bash
# Stop - the real gate. Blocks the turn from ending while the project is not green.
# Catches what the per-edit hook structurally cannot: cross-module type errors,
# failing tests, and files written through Bash rather than Edit.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
. "$(dirname "${BASH_SOURCE[0]}")/_guard.sh"
cd "$FORGE_PROJECT_DIR" || exit 2

if [ ! -f pyproject.toml ]; then
  printf 'BLOCKED: no pyproject.toml at %s - the gate cannot verify this project.\n' "$FORGE_PROJECT_DIR" >&2
  exit 2
fi

fail=""
run() { # name, command...
  local name="$1"; shift
  local out; out=$("$@" 2>&1); local rc=$?
  [ $rc -eq 0 ] || fail="${fail}
--- ${name} ---
${out}"
}

run "ruff format"   uv run ruff format --check .
run "ruff check"    uv run ruff check .
run "mypy (strict)" uv run mypy
[ -d tests ] && run "pytest" uv run pytest -q

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
