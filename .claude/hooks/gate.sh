#!/usr/bin/env bash
# Stop hook: `forge check --fast`. Sources the python template's gate fragments.
set -uo pipefail
_tpl="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../stacks/python/template/.claude/hooks" && pwd)"
. "$_tpl/_common.sh"
. "$_tpl/_guard.sh"
cd "$FORGE_PROJECT_DIR" || exit 2

if [ ! -f src/forge/registry.py ]; then
  printf 'BLOCKED: no src/forge/registry.py at %s - the gate cannot verify this checkout.\n' "$FORGE_PROJECT_DIR" >&2
  exit 2
fi

out=$(uv run forge check --fast 2>&1)
rc=$?

if [ "$rc" -ne 0 ]; then
  digest=$(guard_digest "$out")
  if guard_should_release "$digest"; then
    printf '{"systemMessage":"Gate released after 3 identical failures to avoid a loop - forge is NOT clean, and the gate re-arms on the next turn."}\n'
    exit 0
  fi
  printf 'forge check is red. You are not done. Fix these, then finish:\n%s\n' "$out" >&2
  exit 2
fi
guard_clear
exit 0
