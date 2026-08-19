#!/usr/bin/env bash
# forge-monitor installer.
#
# It writes to ~/.claude/settings.json and nowhere else. It never touches a
# project's .claude/ directory, so the monitor is not in any repo, not in any
# clone, and not in anything a session reads as configuration. Removing it is
# `install.sh --uninstall`, which restores the same file.
#
#   install.sh [--state-dir DIR] [--no-statusline] [--uninstall]
set -euo pipefail

MON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
STATE_DIR="${FORGE_MONITOR_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/forge-monitor}"
WANT_STATUSLINE=1
UNINSTALL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --state-dir) STATE_DIR="$2"; shift 2 ;;
    --no-statusline) WANT_STATUSLINE=0; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

command -v python3 >/dev/null || { echo "forge-monitor: python3 is required" >&2; exit 1; }
command -v jq >/dev/null || echo "forge-monitor: jq not found - events will be recorded in a degraded format" >&2

mkdir -p "$(dirname "$SETTINGS")" "$STATE_DIR"
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
cp "$SETTINGS" "$SETTINGS.forge-monitor.bak"

MON_DIR="$MON_DIR" STATE_DIR="$STATE_DIR" \
WANT_STATUSLINE="$WANT_STATUSLINE" UNINSTALL="$UNINSTALL" \
python3 - "$SETTINGS" <<'PY'
import json, os, sys

path = sys.argv[1]
mon, state = os.environ["MON_DIR"], os.environ["STATE_DIR"]
uninstall = os.environ["UNINSTALL"] == "1"
want_statusline = os.environ["WANT_STATUSLINE"] == "1"
emit = f"{mon}/hooks/emit.sh"

# Deliberately NOT registered: UserPromptSubmit and UserPromptExpansion. A hook
# on those two has its stdout injected into the model's context. The emitter
# prints nothing, so it would be safe today - but a future edit that prints a
# warning would silently start polluting every prompt. Not subscribing is a
# stronger guarantee than remembering to stay quiet.
#
# SessionStart is registered because it is the only way to see a session begin,
# and the same stdout rule applies there: the emitter is silent, and the
# monitor's own test asserts that it is.
EVENTS = [
    "SessionStart", "SessionEnd",
    "Notification",          # permission_prompt / idle_prompt / agent_needs_input
    "Stop", "StopFailure",
    "SubagentStart", "SubagentStop",
    "TeammateIdle",
    "TaskCreated", "TaskCompleted",
    "PreCompact",
]

cfg = json.load(open(path))
hooks = cfg.setdefault("hooks", {})

def is_ours(h):
    return isinstance(h, dict) and "forge-monitor" in str(h.get("command", "")) or \
           isinstance(h, dict) and emit in str(h.get("command", ""))

# Remove any previous install first, so this is idempotent and --uninstall is
# just "the install step, without the add".
for ev in list(hooks):
    groups = hooks.get(ev) or []
    kept_groups = []
    for g in groups:
        g = dict(g)
        g["hooks"] = [h for h in g.get("hooks", []) if not is_ours(h)]
        if g["hooks"]:
            kept_groups.append(g)
    if kept_groups:
        hooks[ev] = kept_groups
    else:
        hooks.pop(ev, None)

if cfg.get("statusLine", {}).get("command", "").find("forge-monitor") >= 0 or \
   cfg.get("statusLine", {}).get("command", "").find(mon) >= 0:
    cfg.pop("statusLine", None)

if not uninstall:
    for ev in EVENTS:
        hooks.setdefault(ev, []).append({
            "hooks": [{
                "type": "command",
                "command": f"bash {emit} {ev}",
                "timeout": 5,
            }]
        })
    if want_statusline:
        cfg["statusLine"] = {"type": "command", "command": f"bash {mon}/statusline.sh"}

if not hooks:
    cfg.pop("hooks", None)

json.dump(cfg, open(path, "w"), indent=2)
print(("uninstalled from " if uninstall else "installed into ") + path)
PY

if [ "$UNINSTALL" = 1 ]; then
  echo "forge-monitor: removed. Backup of the previous file: $SETTINGS.forge-monitor.bak"
  exit 0
fi

[ -f "$STATE_DIR/config.json" ] || cat > "$STATE_DIR/config.json" <<JSON
{
  "sink": { "type": "none" },
  "_github_example": {
    "type": "github",
    "repo": "you/forge-state",
    "branch": "main",
    "token_file": "~/.config/forge-monitor/token"
  },
  "_file_example": { "type": "file", "path": "~/forge-status" }
}
JSON

cat <<TXT

forge-monitor installed.
  hooks      -> $SETTINGS   (user scope only; no project repo was touched)
  state      -> $STATE_DIR
  sink       -> edit $STATE_DIR/config.json  (currently: none, local only)

Run the collector:
  python3 $MON_DIR/collector.py --once      # one pass
  python3 $MON_DIR/collector.py --watch     # daemon

Verify the separation guarantee at any time:
  bash $MON_DIR/verify.sh
TXT
