# stacks

Opinionated technology modules. Each holds a `template/` that the `scaffold`
capability projects into a new project, plus the gates that keep it correct.

| stack | language | gate: on every edit | gate: turn cannot end until |
|---|---|---|---|
| `python` | Python 3.13, uv | ruff (format + lint) on the edited file | ruff + `mypy --strict` + pytest |
| `nextjs` | TypeScript, Next 16 | biome (format + lint + imports) on the edited file | `biome ci` + `tsc --noEmit` + `next build` |

Both ship a multi-stage Dockerfile, a compose file with Postgres and a
healthcheck, and a CLAUDE.md skeleton the owner fills in.

Evidence for every version and config choice:
`capabilities/scaffold/references/verified-stack-facts.md`.
