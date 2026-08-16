#!/usr/bin/env bash
# forge installer — projects the repo into a project or user scope.
# Usage: ./bootstrap/install.sh project <path> | user
set -euo pipefail

FORGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMIT="$(git -C "$FORGE_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'uncommitted')"
MODE="${1:?usage: install.sh project <path> | user}"

link_skills() { # $1 = target .claude dir
  mkdir -p "$1/skills"
  for cap in "$FORGE_ROOT"/capabilities/*/; do
    name="$(basename "$cap")"
    mkdir -p "$1/skills/$name"
    cp "$cap/SKILL.md" "$1/skills/$name/SKILL.md"
    [ -d "$cap/references" ] && cp -r "$cap/references" "$1/skills/$name/"
  done
  cp "$FORGE_ROOT/bootstrap/SKILL.md" "$1/skills/forge-setup/SKILL.md" 2>/dev/null || {
    mkdir -p "$1/skills/forge-setup" && cp "$FORGE_ROOT/bootstrap/SKILL.md" "$1/skills/forge-setup/SKILL.md"; }
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
