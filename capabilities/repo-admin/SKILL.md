---
name: repo-admin
description: Perform GitHub repo infrastructure operations (Pages, settings, CI, secrets-backed admin) autonomously instead of asking the human to click through the UI. Use whenever an approved plan requires a repo operation beyond reading/writing files.
---

# repo-admin

## Decision ladder — use the highest rung available

1. **MCP tool** (GitHub connector, `/mcp/x/all` exposes every toolset — repos, actions, issues…): if a tool covers the operation, use it directly.
2. **Self-serve workflow with GITHUB_TOKEN**: operations GitHub's API allows the workflow's own token to do, the repo does to itself. Verified limit: Pages site *creation* is admin-gated by GitHub (post-CVE policy; "Resource not accessible by integration") — GITHUB_TOKEN can deploy to an existing Pages site but never create one. Run-watching on public repos needs no extra toolset: `api.github.com/repos/<o>/<r>/actions/runs` is world-readable.
3. **Secret-backed reconciler**: admin operations run in an `admin.yml` workflow using a fine-grained PAT stored by the human as a repo secret (`ADMIN_TOKEN`: Administration + Pages write). Trigger it by **push** to a desired-state file (e.g. `.admin/ops.yml`) rather than `workflow_dispatch` — sessions then drive admin with plain contents-write, no extra connector toolset. Build this rung when the second admin need appears; an org-level secret (if repos move to a GitHub org) makes it zero-setup for every future repo.
4. **Escalate**: if no rung reaches the operation, tell the human the exact step, why it's unreachable, and log a friction entry. Known irreducible escalation: first-time Pages enablement on a repo without rung 3 — one click (Settings → Pages → Source: GitHub Actions).

## Creating a new repository

The one procedure with enough failed improvisations to be worth writing down:
`references/new-repo.md` — approval (name, visibility, licence) -> verified
local scaffold -> `create_repository` with `autoInit: false` -> one `push_files`
-> blob-SHA proof -> CI run as the real proof. It also records what the git
API silently drops (file modes) and what still needs a human.

## Rules

- Verify by probing the effect (fetch the URL, read the setting back) — a green workflow run is not proof.
- Irreversible or outward-facing ops (visibility flips, deletions, transfers) gate on explicit plan approval naming the op — rung 3 power does not waive the plan contract.
- Never place credentials in chat, committed files, or projections.

## Verification

Post-op probe demonstrating the effect (URL responds, API state changed). Producer never assumes.

## Report

One SBAR line per operation: what, via which rung, probe result. Escalations always append to FRICTIONS.md.
