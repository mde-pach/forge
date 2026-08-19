# Start a project

```bash
uv run forge scaffold python /path/to/my-api "What it does"
uv run forge scaffold nextjs  /path/to/my-web "What it does"
```

The last line of the output is the only one that matters:

```
verifier : PASS (clean scaffold green twice; broken file blocked)
```

Anything else means the project is not ready. `SKIPPED` means dependencies did
not install, so nothing was proven.

## What you get

| | Python | Next.js |
|---|---|---|
| Package / runtime | uv, `src/` layout | bun, App Router |
| Lint + format | ruff 0.16 defaults | Biome (`recommended` preset, Next/React/test domains) |
| Types | mypy `strict` + `warn_unreachable` | `tsc --noEmit`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` |
| Tests | pytest | optional |
| Build proof | — | `next build` |
| Container | multistage uv image | 3-stage standalone image |
| Compose | app + postgres 18 with a healthcheck | same |
| CI | the same `gate.sh`, on 3.12/3.13/3.14, plus a docker build | the same `gate.sh`, plus a docker build |
| Updates | Dependabot, 3–7 day cooldown | Dependabot, 3–7 day cooldown |
| One entry point | `uv run <name>` | `bun run <name>` |

## The three layers of enforcement

| Layer | Fires | On failure |
|---|---|---|
| `PostToolUse` | after each edit, on that file only (~50 ms) | exit 2 — the diagnostic goes back to Claude |
| `Stop` | when Claude tries to end the turn, on the whole project | exit 2 — the turn cannot end |
| CI | push and pull request | red build |

CI runs the *same script* as the `Stop` hook. There is one definition of green,
so local and CI cannot drift apart. The only difference is the escape hatch:
interactively, three identical failures release the turn once (with a loud
warning) and then re-arm, because a broken gate must not trap a session; CI sets
`FORGE_GATE_NO_RELEASE=1`, because there is nobody to unblock and a release
would turn a red build green.

## Why the gates look paranoid

Every guard below exists because its absence shipped a gate that looked on and
was off:

- **Decisions come from exit codes, never from tool output.** The first version
  grepped ruff's output for a marker string. ruff 0.16 changed the format and
  the check silently passed a broken file.
- **`jq` missing blocks.** The hook cannot read its payload without it, and a
  hook that cannot read its payload was exiting 0.
- **A missing `CLAUDE_PROJECT_DIR` blocks.** It used to exit 0.
- **Hooks are invoked as `bash <script>`.** The GitHub API drops file modes, so
  a pushed-then-cloned hook is not executable; it would exit 127, and Claude
  Code treats any code other than 0 or 2 as non-blocking.
- **The loop guard hashes normalised output.** Build durations made every
  failure unique, so the counter never reached three and the gate deadlocked.
- **The verifier runs the gate twice.** `next build` rewrites `tsconfig.json`,
  which Biome then reported as unformatted forever: green on run 1, red on
  every run after.
- **Python module names are checked for shadowing.** A project called `py`
  imported pytest's transitive `py` package instead of its own source.

## Fill in CLAUDE.md

The scaffold leaves a skeleton on purpose. See
[the CLAUDE.md proposal](/generated/claude-md) for what belongs in it — and
what does not.
