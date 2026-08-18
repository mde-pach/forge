# Shared projection rule: a capability's skill directory IS its source
# directory, minus the manifest, plus whatever the manifest declares under
# `assets:`. Copying only SKILL.md shipped skills that describe scripts that
# were not there.
project_capability() { # $1 = capability source dir, $2 = destination skill dir
  local cap="${1%/}" dest="$2" name
  name="$(basename "$cap")"
  mkdir -p "$dest"
  # Everything in the capability directory except the manifest.
  find "$cap" -mindepth 1 -maxdepth 1 ! -name manifest.yaml -exec cp -R {} "$dest/" \;
  # Declared assets from the repo root.
  if [ -f "$cap/manifest.yaml" ] && command -v python3 >/dev/null; then
    local assets
    assets="$(FORGE_MANIFEST="$cap/manifest.yaml" python3 - <<'PY'
import os, sys
try:
    import yaml
except ImportError:
    sys.exit(0)
m = yaml.safe_load(open(os.environ["FORGE_MANIFEST"])) or {}
for a in (m.get("assets") or []):
    print(a)
PY
)"
    local a
    while IFS= read -r a; do
      [ -n "$a" ] || continue
      [ -e "$FORGE_ROOT/$a" ] || { echo "projection: declared asset '$a' is missing (capability $name)" >&2; return 1; }
      cp -R "$FORGE_ROOT/$a" "$dest/"
    done <<< "$assets"
  fi
  # The exec bit does not survive a git-API push; restore it on projection too.
  find "$dest" -name '*.sh' -exec chmod +x {} \; 2>/dev/null || true
}
