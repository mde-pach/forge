Memory files are concatenated broadest to most specific (managed policy,
`~/.claude/CLAUDE.md`, `./CLAUDE.md`, `./CLAUDE.local.md`); nothing overrides
anything, so the user-scope file holds only what is true in every project.

Anthropic's guidance is under 200 lines per file; this one is about 45 because
its cost is paid in every session. It is delivered as a user message with no
guarantee of compliance, so nothing that must not fail lives here — hooks do
that.

After `/compact`, path-scoped rules are lost until a matching file is read
again, so nothing load-bearing belongs in one. `AGENTS.md` is not read; import
it with `@AGENTS.md`.

Sources: code.claude.com/docs/en/memory, /best-practices, /context-window.
