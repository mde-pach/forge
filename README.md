# forge

An operating framework for working with Claude — across Claude Code, the Claude
app and Cowork. It is where the things I do repeatedly live and are maintained:
project scaffolding, quality gates, research and validation capabilities, and a
view of what my sessions are doing.

## One way in

```bash
uv run forge            # what forge can do
uv run forge start      # the session view: local, and on your phone
uv run forge check      # every check forge makes about itself
uv run forge docs       # build the documentation site
```

Three commands, and only one of them is really for typing. `check` is what the
Stop hook and CI run; `docs` is what CI runs. `uv` exposes only what
`pyproject.toml` declares, so a script on disk that is not declared cannot be
invoked — the mechanism that stops a second way of doing the same job appearing
beside the first.

There were seven. Three of them — `expose`, `doctor`, `parity` — had no caller
anywhere, and `forge check` reported `7 commands, 7 distinct roles` while that
was true: it counted, it did not ask whether anything reached what it counted.
The roles are a closed list now, so a fourth command needs a deliberate edit to
it, and a declared command that nothing invokes is a failure.

## What forge can do

Clone this repository, open Claude Code in it, and ask. These are project skills
in `.claude/skills/`, which Claude Code discovers by scanning — no plugin, no
marketplace, no install step, and an edit takes effect in the session you are
already in.

| Capability | Ask for |
|---|---|
| `scaffold` | a new project, with its quality gates already wired |
| `loop` | forge improving itself — learnings become reviewed diffs |
| `prospect` | a sweep for opportunities worth building |
| `validate` | evidence that an opportunity is real before you build it |
| `repo-admin` | repository administration a session can actually perform |

They are **not** commands, and a scaffolded project does not get them. Forge is
where you ask; a project is where you build. A project gets the gates, the
monitor and the guard — the things that constrain building — and nothing else.

## What's here

- **`src/forge/`** — the registry and the dispatcher. `registry.py` is the list
  of everything forge provides; two entries claiming the same role is an error
  at import, not a review comment.
- **`kernel/`** — how Claude operates under forge. Seven behaviours, small by design.
- **`contract/`** — the capability contract, frozen and versioned.
- **`.claude/skills/`** — the capabilities. Project skills of this repository,
  so a session started here already has them; see below.
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
