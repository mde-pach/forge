# Sourced first by every hook. Two fail-open paths are closed here:
#   1. CLAUDE_PROJECT_DIR unset -> derive the root from this script's location,
#      never `exit 0`.
#   2. jq missing -> the hook cannot read the payload, so it BLOCKS with a
#      message rather than passing silently.
FORGE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$FORGE_PROJECT_DIR" ]; then
  FORGE_PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[1]:-$0}")/../.." && pwd)"
fi
export FORGE_PROJECT_DIR

require_jq() {
  command -v jq >/dev/null && return 0
  printf 'BLOCKED: the quality gate needs `jq` to read the tool payload and it is not on PATH.\nInstall jq, or the gates in this project are not running.\n' >&2
  exit 2
}
