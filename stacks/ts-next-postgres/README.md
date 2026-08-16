# stack: ts-next-postgres (shell)

The first stack module: TypeScript, Next.js, Postgres. Not yet built — populated on first real project need, per forge's need-driven rule.

Will contain, when built:

- **rules/** — path-scoped context (`.claude/rules` format with `paths:` frontmatter): conventions loaded only when matching files are touched.
- **hooks/** — enforcement: typecheck + lint on edit, test gates on stop, protected paths (migrations, env). Boundaries, not sentences.
- **templates/** — project scaffold: tsconfig (strict), eslint, settings.json with hooks wired, CLAUDE.md seed (< 60 lines).
- **verify/** — the mechanical verification chain a plan's criteria can reference: types → lint → unit → e2e smoke.

Everything here is policy plugged into kernel mechanisms; nothing redefines kernel behavior.
