---
name: scaffold
description: Start a new project with forge's process enforcement already wired - Python (uv, ruff, mypy strict) or Next.js (biome, tsc), both with Docker and Claude Code hooks that block on failure. Use when creating a new project or retrofitting gates onto an existing one.
---

# scaffold

## Run it

```bash
bash .claude/skills/scaffold/scaffold.sh python /path/to/my-api "What it does"
bash .claude/skills/scaffold/scaffold.sh nextjs  /path/to/my-web "What it does"
```

The owner says what he wants ("start a Next.js project at ~/code/x that does
Y"); this skill runs the script. The directory name becomes the project name.

Report the last line of the output verbatim. `verifier : PASS` is the only
acceptable result. `FAIL` or `SKIPPED` (dependencies did not install) means the
gates are not proven; say so, do not hand over.

## What gets enforced

Three layers, described in `docs/how-to/start-a-project.md`: a per-edit check
(`PostToolUse`), a whole-project gate the turn cannot end without (`Stop`), and
CI running the same `gate.sh`. The verifier runs the gate twice on the clean
scaffold (`next build` rewrites `tsconfig.json`) and once with a broken file,
which must exit 2.

## Before changing a template

`references/verified-stack-facts.md` records what was checked against the real
tools and when.

## What it refuses

- a target directory that exists and is not empty
- a Python module name owned by the stdlib or resolving to an installed package
- creating a repository, choosing a host, or publishing anything — a separate, approved decision
