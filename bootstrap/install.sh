#!/usr/bin/env bash
# forge installer — projects the repo into a project or user scope.
# Usage: ./bootstrap/install.sh project <path> | user
set -euo pipefail

FORGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMIT="$(git -C "$FORGE_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'uncommitted')"
MODE="${1:?usage: install.sh project <path> | user}"

# shellcheck source=bootstrap/_project.sh
. "$FORGE_ROOT/bootstrap/_project.sh"

link_skills() { # $1 = target .claude dir
  local skills="$1/skills" name
  # Stale skills from a previous install (a capability that has since been
  # deleted) would keep firing. The projection owns this directory.
  rm -rf "$skills"
  mkdir -p "$skills"
  for cap in "$FORGE_ROOT"/capabilities/*/; do
    name="$(basename "$cap")"
    project_capability "$cap" "$skills/$name"
  done
  mkdir -p "$skills/forge-setup"
  cp "$FORGE_ROOT/bootstrap/SKILL.md" "$skills/forge-setup/SKILL.md"
}

case "$MODE" in
  project)
    TARGET="${2:?usage: install.sh project <path>}"
    CD="$TARGET/.claude"
    mkdir -p "$CD"
    link_skills "$CD"
    # Seed CLAUDE.md if absent — small, importing the kernel.
    if [ ! -f "$TARGET/CLAUDE.md" ]; then
      {
        echo "# Project under forge (commit $COMMIT)"
        echo
        echo "@.claude/forge/KERNEL.md"
      } > "$TARGET/CLAUDE.md"
    fi
    mkdir -p "$CD/forge" && cp "$FORGE_ROOT/kernel/KERNEL.md" "$CD/forge/KERNEL.md"
    echo "forge $COMMIT → $TARGET (skills: $(ls "$CD/skills" | tr '\n' ' '))"
    ;;
  user)
    CD="$HOME/.claude"
    mkdir -p "$CD"
    link_skills "$CD"
    echo "forge $COMMIT → $CD (user scope)"
    ;;
  *)
    echo "usage: install.sh project <path> | user" >&2; exit 1;;
esac
