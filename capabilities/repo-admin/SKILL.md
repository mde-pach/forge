---
name: repo-admin
description: Perform GitHub repo infrastructure operations (Pages, settings, CI, secrets-backed admin) autonomously instead of asking the human to click through the UI. Use whenever an approved plan requires a repo operation beyond reading/writing files.
---

# repo-admin

## Decision ladder — use the highest rung available

1. **MCP tool** (GitHub connector, `/mcp/x/all` exposes every toolset — repos, actions, issues…): if a tool covers the operation, use it directly.
2. **Self-serve workflow with GITHUB_TOKEN**: operations GitHub's API allows the workflow's own token to do, the repo does to itself. Example: `actions/configure-pages@v5` with `enablement: true` creates the Pages site on first run — no human click. Encode such operations in workflows triggered by push or `workflow_dispatch` (dispatch and run-watching are in the actions toolset).
3. **Secret-backed workflow**: operations needing elevated rights (e.g. repo visibility) run in an `admin.yml` `workflow_dispatch` workflow using a fine-grained PAT stored once by the human as a repo secret (`ADMIN_TOKEN`, Administration: write, scoped to the one repo). The secret is set once in the UI and never transits chat.
4. **Escalate**: if no rung reaches the operation, tell the human the exact step, why it's unreachable, and log a friction entry. An escalation that repeats is a mechanism gap to close.

## Rules

- Verify by probing the effect (fetch the URL, read the setting back) — a green workflow run is not proof.
- Irreversible or outward-facing ops (visibility flips, deletions, transfers) gate on explicit plan approval naming the op — rung 3 power does not waive the plan contract.
- Never place credentials in chat, committed files, or projections.

## Verification

Post-op probe demonstrating the effect (URL responds, API state changed). Producer never assumes.

## Report

One SBAR line per operation: what, via which rung, probe result. Escalations always append to FRICTIONS.md.
