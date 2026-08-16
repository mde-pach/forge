#!/usr/bin/env bash
# Regenerates dist/ projections from source. dist/ is never hand-edited.
set -euo pipefail

FORGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FORGE_ROOT
COMMIT="$(git -C "$FORGE_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'uncommitted')"
DIST="$FORGE_ROOT/dist"

# Boundary: no projection from invalid sources. Fail loudly, fail early.
python3 - <<'EOF'
import sys, glob, os
os.chdir(os.environ.get("FORGE_ROOT", "."))
try:
    import yaml
except ImportError:
    sys.exit("build: pyyaml required (pip install pyyaml --break-system-packages)")
bad = False
for f in glob.glob("capabilities/*/manifest.yaml"):
    try:
        m = yaml.safe_load(open(f))
        missing = [k for k in ("name","version","need","triggers","context","contract","verifier") if k not in m]
        if missing: print(f"build: {f} missing {missing}"); bad = True
    except yaml.YAMLError as e:
        print(f"build: invalid YAML in {f}: {e}"); bad = True
if bad: sys.exit(1)
EOF

rm -rf "$DIST" && mkdir -p "$DIST/plugin/.claude-plugin" "$DIST/plugin/skills" "$DIST/skills"

# Plugin projection
cat > "$DIST/plugin/.claude-plugin/plugin.json" <<EOF
{
  "name": "forge",
  "description": "maxime's personal operating framework (commit $COMMIT)",
  "version": "0.1.0"
}
EOF
for cap in "$FORGE_ROOT"/capabilities/*/; do
  name="$(basename "$cap")"
  mkdir -p "$DIST/plugin/skills/$name"
  cp "$cap/SKILL.md" "$DIST/plugin/skills/$name/"
  [ -d "$cap/references" ] && cp -r "$cap/references" "$DIST/plugin/skills/$name/"
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
