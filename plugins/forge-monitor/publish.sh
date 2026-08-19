#!/usr/bin/env bash
# Publish one session's record to the store.
#
# Called by the hook, in the background (`async: true`), so nothing here is on
# the critical path of a turn. It writes exactly one file - this session's - so
# two sessions never touch the same path and a rebase always applies cleanly.
# That is the whole reason the store is session-oriented rather than
# machine-oriented: concurrency stops being a design problem.
#
#   bash publish.sh <session-id>
set -uo pipefail

sid="${1:-}"
[ -n "$sid" ] || exit 0

STATE="${FORGE_MONITOR_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/forge-monitor}"
src="$STATE/sessions/${sid}.json"
[ -r "$src" ] || exit 0

cfg="$STATE/config.json"
command -v jq >/dev/null || exit 0
[ -r "$cfg" ] || exit 0
repo=$(jq -r '.store.repo // empty' "$cfg" 2>/dev/null)
branch=$(jq -r '.store.branch // "main"' "$cfg" 2>/dev/null)
[ -n "$repo" ] || exit 0
work="$STATE/store"
url="https://github.com/${repo}.git"

command -v git >/dev/null || exit 0

# Credential, in order: git's helper (gh auth setup-git), then `gh auth token`,
# then a token file. Nothing is stored by us in the first two cases.
auth_url() {
  if git config --get-regexp '^credential\..*helper$' 2>/dev/null | grep -q 'gh auth'; then
    printf '%s' "$url"; return
  fi
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    printf 'https://x-access-token:%s@github.com/%s.git' "$(gh auth token 2>/dev/null)" "$repo"; return
  fi
  local tf; tf=$(jq -r '.store.token_file // empty' "$cfg" 2>/dev/null); tf="${tf/#\~/$HOME}"
  if [ -n "$tf" ] && [ -r "$tf" ]; then
    printf 'https://x-access-token:%s@github.com/%s.git' "$(tr -d '\r\n' < "$tf")" "$repo"; return
  fi
  printf '%s' "$url"
}

if [ ! -d "$work/.git" ]; then
  mkdir -p "$(dirname "$work")"
  if ! git clone --quiet --depth 1 --branch "$branch" "$(auth_url)" "$work" 2>/dev/null; then
    rm -rf "$work"; mkdir -p "$work"
    git -C "$work" init -q -b "$branch" 2>/dev/null || exit 0
    git -C "$work" remote add origin "$url" 2>/dev/null || true
  fi
fi
cd "$work" || exit 0
git remote set-url origin "$url" 2>/dev/null || git remote add origin "$url" 2>/dev/null || true

mkdir -p sessions
cp -f "$src" "sessions/${sid}.json" 2>/dev/null || exit 0
git add "sessions/${sid}.json" >/dev/null 2>&1
git diff --cached --quiet 2>/dev/null && git rev-parse HEAD >/dev/null 2>&1 && exit 0

git -c user.name=forge-monitor -c user.email=forge-monitor@localhost \
  commit -q -m "session ${sid:0:8}: $(jq -r '.state // "?"' "$src")$(jq -r 'if .attention_reason then " (" + .attention_reason + ")" else "" end' "$src")" \
  >/dev/null 2>&1 || exit 0

# Another session may have pushed since. Rebase and retry: records never
# overlap, so this always applies - it is a push race, not a content conflict.
for attempt in 1 2 3; do
  if git push --quiet "$(auth_url)" "HEAD:$branch" 2>/dev/null; then
    python3 - "$src" <<'PY' 2>/dev/null || true
import json, sys
from datetime import datetime, timezone
p = sys.argv[1]
try:
    rec = json.load(open(p))
except Exception:
    raise SystemExit(0)
rec["published_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
json.dump(rec, open(p, "w"), indent=2)
PY
    exit 0
  fi
  git fetch --quiet origin "$branch" 2>/dev/null || break
  git rebase --quiet "origin/$branch" 2>/dev/null || { git rebase --abort 2>/dev/null; break; }
  [ "$attempt" = 3 ] && break
done
exit 0
