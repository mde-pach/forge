---
name: forge-setup
description: Install or update forge — maxime's personal operating framework — in the current surface or project. Use when asked to set up forge, apply the forge operating mode, wire forge into a project, or update forge projections.
---

# forge-setup

forge lives in one git repository (single source of truth). This skill projects it into wherever work happens. Never edit projections; edit the repo and re-project.

## 0. Locate the repo

Find the forge checkout (ask if unknown; clone if given a remote). All steps below read from it.

## 1. Load the operating mode (any surface)

Read `kernel/KERNEL.md` and operate under it for the rest of the session. This is the minimum viable install and costs one file.

## 2. Project into a project (Claude Code)

1. Copy or symlink into the project:
   - `kernel/KERNEL.md` → referenced from a seed `CLAUDE.md` via `@` import (keep the seed under 60 lines)
   - capability `SKILL.md`s → `.claude/skills/<name>/`
   - stack module (if it matches the project) → `.claude/rules/`, hooks into `.claude/settings.json`
2. Wire boundaries before context: hooks and permissions first, guidance second.
3. Verify: run `/context` — standing context added by forge must stay small; if a projection bloats it, the projection is wrong.

## 3. Project into the account (app / Cowork reach)

1. Run `bootstrap/build.sh` to regenerate `dist/` (plugin + account-skill bundles).
2. Install the generated skills at account/user level so every surface sees the manifests (cheap) and loads bodies on demand.

## 4. Update

`git pull` in the repo, re-run the projection for the surfaces in use. Projections carry the repo commit hash so drift is detectable.

## Verification

An install is correct when: kernel behaviors are in force, capability manifests are discoverable, no projection was hand-edited, and standing context grew by less than ~60 lines.

## Report

One SBAR line per surface: what was projected, at which commit, context cost.
