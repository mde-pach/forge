#!/usr/bin/env bash
# GitHub sink — publishes the snapshot into a PRIVATE state repo.
#
# Reads one JSON object on stdin: {config, snapshot, status_md}.
#
# Credentials, in order of preference. The first two need no secret on disk:
#
#   1. git's credential helper. `gh auth setup-git` (once) points git at the
#      GitHub CLI, so a plain `git push` authenticates with the login you
#      already did. Nothing is stored by us, nothing to rotate, and revoking is
#      `gh auth logout`.
#   2. `gh auth token`, read at push time and never written anywhere.
#   3. A token file, for machines with no gh. Last resort, not the default.
#
# Whichever is used, it belongs to THIS process. No Claude Code session has it
# in its environment, so a session cannot publish to, read, or corrupt the state
# store. The observer is not the observed.
set -uo pipefail

payload=$(cat)
command -v jq >/dev/null || { echo "github sink: jq is required"; exit 0; }
printf '%s' "$payload" | jq -e . >/dev/null 2>&1 \
  || { echo "github sink: malformed payload, nothing published"; exit 0; }
cfg() { printf '%s' "$payload" | jq -r ".config.$1 // empty" 2>/dev/null; }

repo=$(cfg repo)            # e.g. mde-pach/forge-state
branch=$(cfg branch); branch="${branch:-main}"
token_file=$(cfg token_file)
work=$(cfg work_dir); work="${work:-${XDG_STATE_HOME:-$HOME/.local/state}/forge-monitor/repo}"
url="https://github.com/${repo}.git"

[ -n "$repo" ] || { echo "github sink: no repo configured"; exit 0; }
command -v git >/dev/null || { echo "github sink: git not found"; exit 0; }

# Resolve an auth strategy once, and say which one is in use - a sink that
# silently stops publishing is worse than one that says why.
auth_mode=""
if git config --get-regexp '^credential\..*helper$' >/dev/null 2>&1 \
   && git config --get-regexp '^credential\..*helper$' | grep -q 'gh auth'; then
  auth_mode="helper"
elif command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  auth_mode="gh-token"
elif [ -n "$token_file" ]; then
  token_file="${token_file/#\~/$HOME}"
  [ -r "$token_file" ] && auth_mode="file"
fi

case "$auth_mode" in
  "") echo "github sink: no credential. Run 'gh auth login && gh auth setup-git', or set config.token_file"; exit 0 ;;
esac

push_url() {  # echoes the URL to push to, with a credential only if needed
  case "$auth_mode" in
    helper) printf '%s' "$url" ;;
    gh-token) printf 'https://x-access-token:%s@github.com/%s.git' "$(gh auth token 2>/dev/null)" "$repo" ;;
    file) printf 'https://x-access-token:%s@github.com/%s.git' "$(tr -d '\r\n' < "$token_file")" "$repo" ;;
  esac
}

if [ ! -d "$work/.git" ]; then
  mkdir -p "$(dirname "$work")"
  if ! git clone --depth 1 --branch "$branch" "$(push_url)" "$work" >/dev/null 2>&1; then
    # An empty repo has no branch to clone; start one locally instead.
    rm -rf "$work"; mkdir -p "$work"
    git -C "$work" init -q -b "$branch" >/dev/null 2>&1 || { echo "github sink: cannot init $work"; exit 0; }
    git -C "$work" remote add origin "$url" >/dev/null 2>&1 || true
  fi
fi

cd "$work" || { echo "github sink: work dir unusable"; exit 0; }

# The stored remote never carries a credential, so a leaked copy of this
# directory leaks nothing.
git remote set-url origin "$url" >/dev/null 2>&1 || git remote add origin "$url" >/dev/null 2>&1 || true
if git fetch --depth 1 origin "$branch" >/dev/null 2>&1; then
  git reset --hard "FETCH_HEAD" >/dev/null 2>&1 || true
fi

host=$(hostname 2>/dev/null || echo unknown)
mkdir -p "sessions/$host"
printf '%s' "$payload" | jq '.snapshot' > "sessions/$host/snapshot.json"

# The store is where machines meet, so the merged view is computed HERE, from
# every host's file, not from the one machine that happens to be pushing.
python3 "$(dirname "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")")/merge.py" . >/dev/null 2>&1 \
  || printf '%s' "$payload" | jq -r '.status_md' > STATUS.md

git add -A >/dev/null 2>&1
if git diff --cached --quiet 2>/dev/null && git rev-parse HEAD >/dev/null 2>&1; then
  echo "no change (auth: $auth_mode)"
  exit 0
fi

waiting=$(printf '%s' "$payload" | jq -r '.snapshot.counts.waiting')
active=$(printf '%s' "$payload" | jq -r '.snapshot.counts.active')
git -c user.name=forge-monitor -c user.email=forge-monitor@localhost \
  commit -q -m "state($host): ${waiting} waiting, ${active} active" >/dev/null 2>&1 || true

if git push "$(push_url)" "HEAD:$branch" >/dev/null 2>&1; then
  echo "pushed ${waiting} waiting / ${active} active (auth: $auth_mode)"
else
  echo "push failed (auth: $auth_mode); state kept locally, retried next pass"
fi
exit 0
