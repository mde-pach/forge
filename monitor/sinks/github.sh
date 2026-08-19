#!/usr/bin/env bash
# GitHub sink — publishes the snapshot into a PRIVATE state repo.
#
# Reads one JSON object on stdin: {config, snapshot, status_md}.
#
# The credential belongs to THIS process. It is read from a file that no
# Claude Code session has in its environment, its working directory, or its
# allowed paths. A session cannot publish, cannot read the state store, and
# cannot corrupt it - which is the point: the observer is not the observed.
set -uo pipefail

payload=$(cat)
cfg() { printf '%s' "$payload" | jq -r ".config.$1 // empty"; }

repo=$(cfg repo)            # e.g. mde-pach/forge-state
branch=$(cfg branch); branch="${branch:-main}"
token_file=$(cfg token_file); token_file="${token_file:-$HOME/.config/forge-monitor/token}"
work=$(cfg work_dir); work="${work:-${XDG_STATE_HOME:-$HOME/.local/state}/forge-monitor/repo}"

[ -n "$repo" ] || { echo "github sink: no repo configured"; exit 0; }
[ -r "$token_file" ] || { echo "github sink: no token at $token_file"; exit 0; }
token=$(tr -d '\r\n' < "$token_file")
[ -n "$token" ] || { echo "github sink: token file is empty"; exit 0; }

host=$(hostname 2>/dev/null || echo unknown)

if [ ! -d "$work/.git" ]; then
  mkdir -p "$(dirname "$work")"
  git clone --depth 1 --branch "$branch" \
    "https://x-access-token:${token}@github.com/${repo}.git" "$work" >/dev/null 2>&1 \
    || { echo "github sink: clone failed"; exit 0; }
fi

cd "$work" || { echo "github sink: work dir unusable"; exit 0; }

# The token is never written into the stored remote. It is supplied per
# invocation and the stored URL stays credential-free, so a leaked repo copy
# leaks nothing.
git remote set-url origin "https://github.com/${repo}.git" >/dev/null 2>&1 || true
git fetch --depth 1 origin "$branch" >/dev/null 2>&1 || true
git reset --hard "origin/$branch" >/dev/null 2>&1 || true

mkdir -p "sessions/$host"
printf '%s' "$payload" | jq -r '.status_md'          > STATUS.md
printf '%s' "$payload" | jq   '.snapshot'            > "sessions/$host/snapshot.json"

git add -A >/dev/null 2>&1
if git diff --cached --quiet 2>/dev/null; then
  echo "no change"
  exit 0
fi

waiting=$(printf '%s' "$payload" | jq -r '.snapshot.counts.waiting')
active=$(printf '%s' "$payload" | jq -r '.snapshot.counts.active')
git -c user.name=forge-monitor -c "user.email=forge-monitor@localhost" \
  commit -q -m "state($host): ${waiting} waiting, ${active} active" >/dev/null 2>&1 || true

if git push "https://x-access-token:${token}@github.com/${repo}.git" "HEAD:$branch" >/dev/null 2>&1; then
  echo "pushed ${waiting} waiting / ${active} active"
else
  echo "push failed (state kept locally, will retry next pass)"
fi
exit 0
