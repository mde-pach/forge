#!/usr/bin/env bash
# Regenerates dist/ projections from source. dist/ is never hand-edited.
set -euo pipefail

FORGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FORGE_ROOT
COMMIT="$(git -C "$FORGE_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'uncommitted')"
DIST="$FORGE_ROOT/dist"

# Boundary: no projection from invalid sources. Fail loudly, fail early.
python3 "$FORGE_ROOT/scripts/validate-manifests.py"

rm -rf "$DIST" && mkdir -p "$DIST/plugin/.claude-plugin" "$DIST/plugin/skills" "$DIST/skills"

# Plugin projection
cat > "$DIST/plugin/.claude-plugin/plugin.json" <<EOF
{
  "name": "forge",
  "description": "maxime's personal operating framework (commit $COMMIT)",
  "version": "0.1.0"
}
EOF
# shellcheck source=bootstrap/_project.sh
. "$FORGE_ROOT/bootstrap/_project.sh"
for cap in "$FORGE_ROOT"/capabilities/*/; do
  project_capability "$cap" "$DIST/plugin/skills/$(basename "$cap")"
done
mkdir -p "$DIST/plugin/skills/forge-setup" && cp "$FORGE_ROOT/bootstrap/SKILL.md" "$DIST/plugin/skills/forge-setup/"

# Standalone account-skill bundles (.skill = zip of the skill dir)
if command -v zip >/dev/null; then
  for skill in "$DIST/plugin/skills"/*/; do
    name="$(basename "$skill")"
    (cd "$skill" && zip -qr "$DIST/skills/$name.skill" .)
  done
fi

echo "dist/ rebuilt at commit $COMMIT"
