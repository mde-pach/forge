# forge

An operating framework for working with Claude — across Claude Code, the Claude
app and Cowork. It is where the things I do repeatedly live and are maintained:
project scaffolding, quality gates, research and validation capabilities, and a
view of what my sessions are doing.

## One way in

```bash
uv run forge            # what forge can do
uv run forge scaffold python ~/code/my-api "What it does"
uv run forge serve      # the session view, on localhost
uv run forge check      # every check forge makes about itself
```

There is exactly one entry point, and `uv` exposes only what
`pyproject.toml` declares. A script that exists on disk but is not declared
cannot be invoked — which is the mechanism that stops a second way of doing the
same job from quietly appearing beside the first. Five of them once did.

## What's here

- **`src/forge/`** — the registry and the dispatcher. `registry.py` is the list
  of everything forge provides; two entries claiming the same role is an error
  at import, not a review comment.
- **`kernel/`** — how Claude operates under forge. Seven behaviours, small by design.
- **`contract/`** — the capability contract, frozen and versioned.
- **`capabilities/`** — created only when a need demonstrates itself.
- **`stacks/`** — opinionated project templates, with their gates.
- **`plugins/`** — Claude Code plugins forge maintains. Loaded at launch, never
  declared by your projects.

Design rationale: `docs/explanation.md`. Evidence: `kernel/SOURCES.md`.
What went wrong and what was done about it: `FRICTIONS.md`.

## Setup

`docs/how-to/monitor.md` for the session view.
`docs/how-to/connect-github.md` for GitHub access.
`docs/how-to/start-a-project.md` for scaffolding.

Docs: https://mde-pach.github.io/forge/ — repo: https://github.com/mde-pach/forge

## Changing forge

Every change goes through the loop capability: learnings become reviewed diffs.
`uv run forge check` must be clean, and it is deliberately not a check I can
satisfy by being confident — it fails on files nothing runs, on two mechanisms
claiming one role, and on checks that pass without testing anything.
