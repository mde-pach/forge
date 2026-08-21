---
name: repo-admin
description: Perform GitHub repo infrastructure operations (Pages, settings, CI, secrets-backed admin) autonomously instead of asking the human to click through the UI. Use whenever an approved plan requires a repo operation beyond reading/writing files.
---

# repo-admin

## Decision ladder — highest rung available

1. **MCP tool**: the GitHub connector at `/mcp/x/all` exposes every toolset.
2. **Self-serve workflow with `GITHUB_TOKEN`**: what the API lets a repo do to
   itself. It can deploy to an existing Pages site but never create one; run
   watching on public repos is world-readable.
3. **Secret-backed reconciler**: an `admin.yml` workflow using a fine-grained
   PAT stored as `ADMIN_TOKEN` (Administration + Pages write), triggered by a
   push to a desired-state file such as `.admin/ops.yml`. Build it at the
   second admin need.
4. **Escalate**: name the exact step, why it is unreachable, and record a
   friction in forge-state. Known irreducible case: first-time Pages
   enablement without rung 3 (Settings → Pages → Source: GitHub Actions).

## Creating a new repository

`references/new-repo.md`: approval (name, visibility, licence) → verified local
scaffold → `create_repository` with `autoInit: false` → one `push_files` →
blob-SHA proof → CI run as the real proof.

## Rules

- Verify by probing the effect; a green run is not proof.
- Irreversible or outward-facing operations gate on plan approval naming them.
- Credentials never enter chat, committed files or projections.

## Verification

Post-op probe demonstrating the effect (URL responds, API state changed).

## Report

One SBAR line per operation: what, via which rung, probe result. Escalations are
recorded as frictions in forge-state.
