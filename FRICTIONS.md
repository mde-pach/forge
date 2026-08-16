# Frictions — the loop's raw intake

Observed friction points, appended as they occur. Each either becomes a boundary/capability diff (then gets removed here) or is accepted with a reason. Owned by the loop capability.

| # | Date | Friction | Status |
|---|------|----------|--------|
| 1 | 2026-08-16 | Cloud sessions are ephemeral → git credentials don't persist across sessions. | closed — GitHub's official remote MCP server as an account-level custom connector (docs/how-to/connect-github.md); registry lacked it, but custom connectors accept any remote MCP URL |
| 2 | 2026-08-16 | Capability manifests were hand-written and shipped with invalid YAML twice. | closed — validation boundary added to bootstrap/build.sh (commit 6c531a2) |
| 3 | 2026-08-16 | forge exists only in one session's container until pushed; a reclaimed container = lost history since last delivery. | open — mitigated by zip deliveries; solved by GitHub push |
