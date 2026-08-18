# Verified stack facts (2026-08-18)

Every choice in the templates traces to something checked in this environment or
fetched from a primary source. Facts rot; re-verify before trusting.

## Claude Code hooks

- Schema nests **event → matcher group → handler**; handler needs `type`
  (`command`|`http`|`mcp_tool`|`prompt`|`agent`). With `args: []` present the
  command is spawned directly (no shell) — that is why the templates pass `args`.
- **`PostToolUse` cannot cancel an edit.** Exit 2 shows stderr *to Claude*, which
  self-corrects. **`Stop` exit 2 prevents the turn from ending** and feeds stderr
  back as the next instruction. That asymmetry is why the fast check is advisory-
  by-nature and the gate is the enforcement point.
- Exit codes: 0 = fine, 2 = blocking, **anything else = non-blocking error, the
  action proceeds**. A missing `chmod +x` yields 127 → a gate that silently
  enforces nothing. The scaffold sets the bit and asserts it.
- stdin payload for PostToolUse is `{tool_name, tool_input, tool_response,
  tool_use_id}`; the edited path is `.tool_input.file_path` (NOT `tool_result`,
  NOT `edits[]` — both appear in bad summaries).
- The `if:` field filters by permission-rule syntax (`Edit(**/*.py)`) but is
  best-effort and holds exactly one rule, so the templates filter **inside the
  script** on the file path.
- `${CLAUDE_PROJECT_DIR}` is available; hooks in project `.claude/settings.json`
  do not run until workspace trust is accepted.
- `.claude/rules/*.md` with `paths:` frontmatter is real; those rules load when a
  matching file is read, and are **not** re-injected after `/compact`. Context,
  never enforcement — which is the whole reason the gates are hooks.

## Python

| Tool | Verified | Note |
|---|---|---|
| uv | 0.12.5 latest (0.8.17 in this sandbox) | `uv_build` is the default backend; dev deps in `[dependency-groups]` (PEP 735) |
| ruff | 0.16.3 | **0.16 raised the default rule set from 59 to 413 rules.** A large `select` list is now an anti-pattern; the template only `extend-select`s what defaults leave out |
| mypy | 2.3.1 | `--strict` now includes `--extra-checks`; `strict_bytes` on by default |
| ty / pyrefly | 0.0.72 beta / 1.2.0 stable | Alternatives; mypy remains the conservative gate |

`select = ["ALL"]` is explicitly discouraged upstream: it opts you into every
future rule on upgrade. `disallow_any_explicit` was considered and rejected —
it bans deliberate `Any` and is impractical against third-party APIs.

Verified locally on a fresh scaffold: ruff clean, `ruff format --check` clean,
mypy strict clean, pytest green.

## Next.js

| Tool | Verified | Note |
|---|---|---|
| next | 16.3.1 | **Turbopack is the default bundler** and does **not** type-check — `tsc --noEmit` must be its own gate step |
| @biomejs/biome | 2.5.9 | 2.x moved `organizeImports` under `assist.actions.source`; `linter.rules.recommended` became `preset`; `domains` gates the next/react/test/types rule packs |
| typescript | 5.9.3 installed (7.0.2 is latest npm `latest`) | TS 7 is the native Go compiler; the template stays on 5.x until a project opts in |

Biome type-aware rules (e.g. `noFloatingPromises`) are **nursery** — the template
enables that one explicitly, since `domains.types` alone did not fire it in testing.
`noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` are in `tsc --init`'s
generated defaults as of TS 7 and are on in the template.

Verified locally on a fresh scaffold: `biome ci` clean, `tsc --noEmit` clean.

## Docker

- Python image follows `astral-sh/uv-docker-example/multistage.Dockerfile`:
  two-step `uv sync --locked` (deps layer cached before source), `UV_PYTHON_DOWNLOADS=0`.
  **Builder and runtime must share the Python minor version** — the venv hardcodes
  the interpreter path.
- Next image follows `vercel/next.js/examples/with-docker`: three stages, requires
  `output: "standalone"`, runs as `node`.
- Compose: the top-level `version:` key is obsolete; `name:` is used instead.
  `depends_on.condition: service_healthy` plus a `pg_isready` healthcheck.

**Unverified in this sandbox:** container registry egress is blocked, so no image
was pulled or built, and the `python3.14` uv tag was not confirmed. The templates
pin 3.13 / node 22-slim, which are conservative. Verify on first `docker compose build`.
