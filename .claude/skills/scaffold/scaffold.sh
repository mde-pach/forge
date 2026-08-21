#!/usr/bin/env bash
# scaffold.sh <python|nextjs> <dir> [description] - run by the `scaffold` skill.
set -euo pipefail

# Walk up to the stacks tree rather than hard-coding this file's depth.
_here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORGE_ROOT=""
_d="$_here"
while [ "$_d" != "/" ]; do
  if [ -d "$_d/stacks" ] && [ -f "$_d/pyproject.toml" ]; then FORGE_ROOT="$_d"; break; fi
  _d="$(dirname "$_d")"
done
if [ -z "$FORGE_ROOT" ]; then
  echo "scaffold: no forge checkout above $_here - cannot find the stacks/ tree" >&2
  exit 1
fi
stack="${1:?usage: scaffold.sh <python|nextjs> <target-dir> [description]}"
target="${2:?usage: scaffold.sh <python|nextjs> <target-dir> [description]}"
description="${3:-}"

tpl="$FORGE_ROOT/stacks/$stack/template"
[ -d "$tpl" ] || { echo "scaffold: unknown stack '$stack' (have: $(ls "$FORGE_ROOT/stacks" | tr '\n' ' '))" >&2; exit 1; }
[ -e "$target" ] && [ -n "$(ls -A "$target" 2>/dev/null)" ] && { echo "scaffold: '$target' exists and is not empty - refusing" >&2; exit 1; }

project="$(basename "$target")"
module="$(printf '%s' "$project" | tr '[:upper:]-' '[:lower:]_' | tr -cd '[:alnum:]_')"
[ -n "$module" ] || { echo "scaffold: '$project' yields an empty python module name - pick another name" >&2; exit 1; }
case "$module" in [0-9]*) echo "scaffold: module name '$module' starts with a digit - pick another name" >&2; exit 1 ;; esac

# Refuse a module name the stdlib or an installed package would shadow.
if [ "$stack" = python ] && command -v python3 >/dev/null; then
  if python3 -c "import sys; sys.exit(0 if '$module' in sys.stdlib_module_names else 1)" 2>/dev/null; then
    echo "scaffold: module name '$module' collides with a Python standard-library module - pick another name" >&2
    exit 1
  fi
fi
[ -n "$description" ] || description="$project"
# Metadata must be single-line.
description=$(printf '%s' "$description" | tr -d '\000-\037' | tr -s ' ')

created_target=0
[ -d "$target" ] || created_target=1
cleanup() { [ "$created_target" = 1 ] && rm -rf "$target"; }
# shellcheck disable=SC2154
trap 'rc=$?; [ $rc -ne 0 ] && cleanup; exit $rc' EXIT

mkdir -p "$target"
cp -R "$tpl/." "$target/"

# Rename placeholder module directory (python stack).
[ -d "$target/src/__MODULE__" ] && mv "$target/src/__MODULE__" "$target/src/$module"

# Placeholder substitution by parameter expansion (no sed injection); `&` escaped for bash 5.2.
amp_esc() { printf '%s' "${1//&/\\&}"; }
subst_file() {
  local f="$1" content
  IFS= read -r -d '' content < "$f" || true
  content="${content//__PROJECT__/$(amp_esc "$project")}"
  content="${content//__MODULE__/$(amp_esc "$module")}"
  content="${content//__DESCRIPTION__/$(amp_esc "$description")}"
  printf '%s' "$content" > "$f"
}
while IFS= read -r -d '' f; do
  case "$f" in *.png|*.jpg|*.ico|*.woff*|*/.git/*) continue ;; esac
  subst_file "$f"
done < <(find "$target" -type f -print0)

# The exec bit does not survive a git-API push; set it every time.
chmod +x "$target"/.claude/hooks/*.sh
for h in "$target"/.claude/hooks/*.sh; do
  case "$h" in *_guard.sh) continue ;; esac
  [ -x "$h" ] || { echo "scaffold: FAILED to make $h executable" >&2; exit 1; }
done

command -v jq >/dev/null || echo "scaffold: WARNING - jq not found; the hooks will block until it is installed" >&2

# Lockfile: the gate and the Dockerfile need it.
installed=0
case "$stack" in
  python)
    if command -v uv >/dev/null && (cd "$target" && uv sync >/dev/null 2>&1); then installed=1; fi ;;
  nextjs)
    if command -v bun >/dev/null && (cd "$target" && bun install >/dev/null 2>&1); then installed=1; fi ;;
esac

# The module must resolve to src/, not to a same-named installed package.
if [ "$stack" = python ] && [ "$installed" = 1 ]; then
  resolved=$( (cd "$target" && uv run python -c "import $module,sys; sys.stdout.write($module.__file__ or '')" 2>/dev/null) || true )
  case "$resolved" in
    "$target"/src/*) : ;;
    "") echo "scaffold: WARNING - could not resolve module '$module' after install" >&2 ;;
    *)  echo "scaffold: module '$module' resolves to $resolved, not this project's src/ - the name is shadowed by an installed package. Pick another name." >&2
        exit 1 ;;
  esac
fi

# Verify.
verify_result="SKIPPED (dependencies not installed - no network?)"
if [ "$installed" = 1 ]; then
  green=0; blocks=0
  # Twice: `next build` rewrites tsconfig.json, so green must also be idempotent.
  ( cd "$target" && CLAUDE_PROJECT_DIR="$PWD" bash .claude/hooks/gate.sh </dev/null >/dev/null 2>&1 ) || green=-1
  if [ "$green" = 0 ]; then
    ( cd "$target" && CLAUDE_PROJECT_DIR="$PWD" bash .claude/hooks/gate.sh </dev/null >/dev/null 2>&1 ) && green=1 || green=-2
  fi
  rm -f "$target/.claude/.gate-state"
  case "$stack" in
    python) probe="src/$module/_scaffold_probe.py"; printf 'import os\ndef f( x ):\n  y=1\n  return x\n' > "$target/$probe" ;;
    nextjs) probe="src/app/_scaffold_probe.ts"; printf "export const x='y'\n" > "$target/$probe" ;;
  esac
  probe_rc=0
  ( cd "$target" && printf '{"tool_input":{"file_path":"%s"}}' "$probe" | CLAUDE_PROJECT_DIR="$PWD" bash .claude/hooks/fast-check.sh >/dev/null 2>&1 ) || probe_rc=$?
  [ "$probe_rc" -eq 2 ] && blocks=1
  rm -f "$target/$probe"
  if [ "$green" = 1 ] && [ "$blocks" = 1 ]; then
    verify_result="PASS (clean scaffold green twice; broken file blocked)"
  else
    verify_result="FAIL (gate green=$green [-1=first run red, -2=NOT IDEMPOTENT], probe blocked=$blocks)"
    echo "scaffold: VERIFIER FAILED - the gates are not working in $target" >&2
  fi
fi

# Say what was enabled.
cat <<EOF
scaffolded $stack -> $target
  project  : $project
  module   : $module
  verifier : $verify_result
  plugins  : forge-monitor (session records -> your store), forge-guard (blocks
             unreviewed changes to hooks, settings, manifests and CI).
             Enabled in $target/.claude/settings.json, which is COMMITTED - so
             it applies to anyone who opens this repository. Remove the
             enabledPlugins block to opt out.
next:
EOF
case "$stack" in
  python) echo "  cd $target && uv run pytest" ;;
  nextjs) echo "  cd $target && bun run dev" ;;
esac
echo "  then fill in CLAUDE.md (it is a skeleton on purpose)"
