# Frictions — the loop's raw intake

Observed friction points, appended as they occur. Each either becomes a boundary/capability diff (then gets removed here) or is accepted with a reason. Owned by the loop capability.

| # | Date | Friction | Status |
|---|------|----------|--------|
| 1 | 2026-08-16 | Cloud sessions are ephemeral → git credentials don't persist across sessions. | closed — GitHub's official remote MCP server as an account-level custom connector (docs/how-to/connect-github.md); registry lacked it, but custom connectors accept any remote MCP URL |
| 2 | 2026-08-16 | Capability manifests were hand-written and shipped with invalid YAML twice. | closed — validation boundary added to bootstrap/build.sh (commit 6c531a2) |
| 3 | 2026-08-16 | forge exists only in one session's container until pushed; a reclaimed container = lost history since last delivery. | closed — canonical remote: https://github.com/mde-pach/forge (mirrored 2026-08-16) |
| 4 | 2026-08-16 | Custom connectors can't be created from the mobile app (browse-only), and GitHub lacks DCR so OAuth needs a user-created OAuth App — two undocumented detours during setup. | closed — verified procedure written into docs/how-to/connect-github.md |
| 5 | 2026-08-16 | GitHub API pushes (push_files) drop the executable bit — cloned scripts aren't runnable as ./script.sh. | closed — documented invocation is mode-independent (`bash script.sh`); content verified byte-identical via blob SHAs |
| 6 | 2026-08-16 | Session chose a hosting provider (Vercel) the owner never asked for — an infrastructure decision made outside the plan. | closed — corrected to GitHub Pages; rule reinforced: infra/provider choices are plan-level and must be explicit in the approved plan |
| 7 | 2026-08-16 | Repo administration (enable Pages, settings) had no session-reachable mechanism — sessions asked the human to click through GitHub UI. | closed — repo-admin capability: MCP tools → self-serve workflows (configure-pages enablement:true) → secret-backed admin workflow → escalate-and-log; connector standard raised to /mcp/x/all |
| 8 | 2026-08-16 | configure-pages enablement:true failed ("Resource not accessible by integration"): GitHub admin-gates Pages *creation* post-CVE — no session-reachable token can do it. | closed — rung ladder corrected in repo-admin; irreducible one-click enablement documented and performed 2026-08-16 (Source: GitHub Actions); rung-3 push-driven ADMIN_TOKEN reconciler specified for when the second admin need appears |
