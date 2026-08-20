#!/usr/bin/env bash
# Stop - forge's gate on forge.
#
# Forge installed a Stop-hook gate into every project it scaffolded and had none
# on itself: `forge check` was run by CI and by whoever remembered to type it.
# Four days of additive drift got in through that gap - every correction built
# the new thing and left the old one, and nothing noticed until a human read the
# whole tree. This is the mechanism that would have caught it at the turn it was
# created.
#
# It runs the READ-ONLY half (`--fast`). The full run breaks things on purpose to
# prove the checks work - it appends a bogus command to a template README - and
# doing that while a session is editing the same tree races it. That half is CI's.
#
# The two fragments below are sourced from the python template rather than
# copied, so forge's own gate IS the gate it ships. A regression in the loop
# guard breaks this repo before it can reach a scaffolded project.
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
