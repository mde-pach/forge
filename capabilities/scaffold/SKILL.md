---
name: scaffold
description: Start a new project with forge's process enforcement already wired - Python (uv, ruff, mypy strict) or Next.js (biome, tsc), both with Docker and Claude Code hooks that block on failure. Use when creating a new project or retrofitting gates onto an existing one.
---

# scaffold

## Run it

```bash
bash capabilities/scaffold/scaffold.sh python /path/to/my-api  "What it does"
bash capabilities/scaffold/scaffold.sh nextjs /path/to/my-web  "What it does"
```

The directory name becomes the project name; a Python module name is derived
from it. Placeholders are substituted, hook scripts are made executable, and
the next commands are printed.

## What gets enforced, and where

Two layers, because they catch different things:

| Layer | Fires | Runs | On failure |
|---|---|---|---|
| `PostToolUse` | after each file edit | ruff / biome on **that file** (~50ms) | exit 2 - diagnostics go back to Claude, which self-corrects |
| `Stop` | when Claude tries to finish the turn | the **whole project**: ruff + mypy --strict + pytest, or biome ci + tsc --noEmit + tests | exit 2 - the turn cannot end |

The Stop gate is the real one. It catches what per-file checks structurally
cannot: cross-module type errors, broken tests, and files written through Bash
rather than Edit. A loop guard releases the turn after three identical
failures, with a loud warning, so a broken gate cannot trap a session.

## Verify before handing over

Never report a scaffold as done without running both halves of its own verifier:

```bash
cd <target> && echo '{}' | ./.claude/hooks/gate.sh; echo "expect 0"
printf 'x=1\n def f( ):pass\n' > src/<module>/_probe.py     # or a .tsx equivalent
echo '{"tool_input":{"file_path":"src/<module>/_probe.py"}}' | ./.claude/hooks/fast-check.sh; echo "expect 2"
rm src/<module>/_probe.py
```

A hook that is not executable exits 127 and is treated as a non-blocking error:
the gate looks installed and enforces nothing. That is why the probe is not optional.

## Requirements

`jq` must be on PATH - the hooks read the tool payload with it. Python stack
needs `uv`; Next.js stack needs Node and npm.

## After scaffolding

Fill in `CLAUDE.md` - it ships as a skeleton on purpose. Anything file-specific
belongs in `.claude/rules/*.md` with `paths:` frontmatter, which loads only when
a matching file is read.

## Report

SBAR: what was scaffolded, the two verifier results (green scaffold / blocked
probe), and what the owner must fill in.

Stack details and the evidence behind every version and config choice:
`references/verified-stack-facts.md`.
