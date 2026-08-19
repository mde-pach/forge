#!/usr/bin/env bash
# file sink — writes the snapshot to a directory. The reference implementation
# of "the sink is replaceable": same stdin contract, twelve lines, no network.
set -uo pipefail
payload=$(cat)
dest=$(printf '%s' "$payload" | jq -r '.config.path // empty')
[ -n "$dest" ] || { echo "file sink: no path configured"; exit 0; }
mkdir -p "$dest" || { echo "file sink: cannot create $dest"; exit 0; }
printf '%s' "$payload" | jq -r '.status_md' > "$dest/STATUS.md"
printf '%s' "$payload" | jq   '.snapshot'   > "$dest/snapshot.json"
echo "wrote $dest"
