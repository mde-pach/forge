# forge

A personal operating framework for working with Claude — across Claude Code, the Claude app, and Cowork. Repo-first: this repository is the single source of truth; everything installed elsewhere is generated from it.

## What it is

- **kernel/** — how Claude operates under forge, always and everywhere. Seven behaviors. Small by design.
- **contract/** — the capability contract (frozen, versioned). Every capability, present or future, conforms to it.
- **capabilities/** — capability instances. Created only when a need demonstrates itself, never speculatively.
- **stacks/** — opinionated technology modules plugged into capabilities that touch code.
- **bootstrap/** — the self-installing skill. Projects forge into a project, an account, or a session.
- **dist/** — generated projections (plugin, account skills). Never hand-edited.

## Why it's shaped this way

Microkernel pattern: the kernel is mechanism, capabilities are policy. The contract is the one deliberately up-front investment; everything else is added on demonstrated need. Design rationale and evidence base: `kernel/SOURCES.md`.

## Install

```
./bootstrap/install.sh project /path/to/project   # wire forge into a project
./bootstrap/install.sh user                       # wire forge into ~/.claude
./bootstrap/build.sh                              # regenerate dist/ projections
```

Or, in any Claude surface with the forge-setup skill available: ask for forge setup.

## Evolving forge

Changes to forge go through the loop capability: learnings are proposed as diffs, reviewed, committed. The contract evolves only by weakening preconditions or strengthening postconditions; deprecate, don't delete. Periodic factorization passes keep the whole thing small.
