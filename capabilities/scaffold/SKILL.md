---
name: scaffold
description: Start a new project with forge's process enforcement already wired - Python (uv, ruff, mypy strict) or Next.js (biome, tsc), both with Docker and Claude Code hooks that block on failure. Use when creating a new project or retrofitting gates onto an existing one.
---

# scaffold

## Run it

```bash
# installed as a skill (the usual case)
bash .claude/skills/scaffold/scaffold.sh python /path/to/my-api "What it does"
bash .claude/skills/scaffold/scaffold.sh nextjs /path/to/my-web "What it does"

# from a forge checkout
bash capabilities/scaffold/scaffold.sh python /path/to/my-api "What it does"
```

The directory name becomes the project name; a Python module name is derived
from it. Placeholders are substituted, hook scripts are made executable, and
the next commands are printed.

## What gets enforced, and where

Three layers, because they catch different things:

| Layer | Fires | Runs | On failure |
|---|---|---|---|
| `PostToolUse` | after each file edit | ruff / biome on **that file** (~50ms) | exit 2 — diagnostics go back to Claude, which self-corrects |
| `Stop` | when Claude tries to finish the turn | the **whole project**: ruff + mypy --strict + pytest, or biome ci + tsc --noEmit + next build | exit 2 — the turn cannot end |
| CI | on push and PR | **the same `gate.sh`**, plus a docker build | the build is red |

The Stop gate is the real one. It catches what per-file checks structurally
cannot: cross-module type errors, broken tests, and files written through Bash
rather than Edit.

CI deliberately executes the same script rather than a parallel list of steps.
There is one definition of green, so local and CI cannot drift — only the
escape hatch differs: the interactive loop guard releases a turn after three
identical failures (then re-arms), while CI sets `FORGE_GATE_NO_RELEASE=1`,
because in CI there is no human to unblock and a release would turn a red build
green.

## Verify before handing over

The script verifies itself and prints the result; a scaffold is only done when
that line reads `verifier : PASS`. It runs three checks, and each exists because
the absence of it shipped a broken gate at least once:

```
clean gate run 1 -> 0    the scaffold is green
clean gate run 2 -> 0    and STAYS green: `next build` rewrites tsconfig.json,
                         which made run 2 red forever while run 1 looked fine
broken-file probe -> 2   the fast check actually blocks
```

If the line reads `FAIL` or `SKIPPED`, the project is not ready to hand over —
report that, do not paper over it. `SKIPPED` means dependencies did not install
(usually no network), so nothing was proven.

## What it refuses

- a target directory that exists and is not empty
- a Python module name owned by the standard library, or one that resolves to an
  installed package instead of the project's own `src/` (`py`, for instance, is
  shipped transitively by pytest and would silently shadow the project)
- creating a repository, choosing a host, or publishing anything — that is a
  separate, approved decision
