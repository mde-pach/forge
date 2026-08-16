# Frictions — the loop's raw intake

Observed friction points, appended as they occur. Each either becomes a boundary/capability diff (then gets removed here) or is accepted with a reason. Owned by the loop capability.

| # | Date | Friction | Status |
|---|------|----------|--------|
| 1 | 2026-08-16 | Cloud sessions are ephemeral → git credentials don't persist; push access must be re-granted per session (see docs/how-to/give-push-access.md). No GitHub connector in the MCP registry to solve it durably. | open — re-check registry periodically |
| 2 | 2026-08-16 | Capability manifests were hand-written and shipped with invalid YAML twice. | closed — validation boundary added to bootstrap/build.sh (commit 6c531a2) |
| 3 | 2026-08-16 | forge exists only in one session's container until pushed; a reclaimed container = lost history since last delivery. | open — mitigated by zip deliveries; solved by GitHub push |
