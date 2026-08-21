# forge

An operating framework for working with Claude — across Claude Code, the Claude
app and Cowork. It holds the things I do repeatedly: project scaffolding,
quality gates, research and validation capabilities, and a view of what my
sessions are doing.

## Commands

```bash
uv run forge            # what forge can do
uv run forge start      # the session view: local, and on your phone
uv run forge check      # every check forge makes about itself (Stop hook, CI)
uv run forge docs       # build the documentation site (CI)
```

`uv` exposes only what `pyproject.toml` declares, so a script on disk that is
not declared cannot be invoked.

## Capabilities

Clone this repository, open Claude Code in it, and ask. These are project skills
in `.claude/skills/`; Claude Code discovers them by scanning, so there is
nothing to install.

| Capability | Ask for |
|---|---|
| `scaffold` | a new project, with its quality gates already wired |
| `loop` | forge improving itself — learnings become reviewed diffs |
| `prospect` | a sweep for opportunities worth building |
| `validate` | evidence that an opportunity is real before you build it |
| `repo-admin` | repository administration a session can actually perform |

A scaffolded project does not get them. Forge is where you ask; a project is
where you build. A project gets the gates, the monitor and the guard — the
things that constrain building — and nothing else.

## Layout

- **`src/forge/`** — the registry (`registry.py`: everything forge provides,
  one entry per role) and the dispatcher.
- **`kernel/`** — how Claude operates under forge. Seven behaviours.
- **`contract/`** — the capability contract, frozen and versioned.
- **`.claude/skills/`** — the capabilities.
- **`stacks/`** — project templates, with their gates.
- **`plugins/`** — Claude Code plugins forge maintains: the monitor and the guard.
- **`tests/`** — the test suite, run by `forge check` and CI.

Design rationale: `docs/explanation.md`. Evidence: `kernel/SOURCES.md`.
Open frictions live in the owner's private `forge-state` repository, not here.

## Setup

`docs/how-to/monitor.md` for the session view.
`docs/how-to/connect-github.md` for GitHub access.
`docs/how-to/start-a-project.md` for scaffolding.

Docs: https://mde-pach.github.io/forge/ — repo: https://github.com/mde-pach/forge

## Changing forge

Every change goes through the `loop` capability: learnings become reviewed
diffs. `uv run forge check` must be clean.
