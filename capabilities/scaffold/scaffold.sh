#!/usr/bin/env bash
# scaffold - project a forge stack into a new project directory.
#
#   bash scaffold.sh <stack> <target-dir> [description]
#
# Stacks: python | nextjs   (see forge/stacks/)
set -euo pipefail

FORGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
stack="${1:?usage: scaffold.sh <python|nextjs> <target-dir> [description]}"
target="${2:?usage: scaffold.sh <python|nextjs> <target-dir> [description]}"
description="${3:-}"

tpl="$FORGE_ROOT/stacks/$stack/template"
[ -d "$tpl" ] || { echo "scaffold: unknown stack '$stack' (have: $(ls "$FORGE_ROOT/stacks" | tr '\n' ' '))" >&2; exit 1; }
[ -e "$target" ] && [ -n "$(ls -A "$target" 2>/dev/null)" ] && { echo "scaffold: '$target' exists and is not empty - refusing" >&2; exit 1; }

project="$(basename "$target")"
module="$(printf '%s' "$project" | tr '[:upper:]-' '[:lower:]_' | tr -cd '[:alnum:]_')"
[ -n "$description" ] || description="$project"

mkdir -p "$target"
cp -R "$tpl/." "$target/"

# Rename placeholder module directory (python stack).
[ -d "$target/src/__MODULE__" ] && mv "$target/src/__MODULE__" "$target/src/$module"

# Substitute placeholders in every text file.
find "$target" -type f -print0 | while IFS= read -r -d '' f; do
  case "$f" in *.png|*.jpg|*.ico|*.woff*|*/.git/*) continue ;; esac
  sed -i \
    -e "s|__PROJECT__|$project|g" \
    -e "s|__MODULE__|$module|g" \
    -e "s|__DESCRIPTION__|$description|g" "$f"
done

# The exec bit does not survive a git-API push (forge friction #5), and a hook
# that is not executable fails silently with code 127 - the gate would be off
# while looking on. Set it here, every time, and prove it.
chmod +x "$target"/.claude/hooks/*.sh
for h in "$target"/.claude/hooks/*.sh; do
  case "$h" in *_guard.sh) continue ;; esac
  [ -x "$h" ] || { echo "scaffold: FAILED to make $h executable" >&2; exit 1; }
done

# jq is a hard dependency of the hooks: without it every hook exits 0 silently.
command -v jq >/dev/null || echo "scaffold: WARNING - jq not found; the hooks need it to read the tool payload" >&2

cat <<EOF
scaffolded $stack -> $target
  project : $project
  module  : $module
next:
EOF
case "$stack" in
  python) echo "  cd $target && uv sync && uv run pytest" ;;
  nextjs) echo "  cd $target && npm install && npm run typecheck" ;;
esac
echo "  then fill in CLAUDE.md (it is a skeleton on purpose)"
