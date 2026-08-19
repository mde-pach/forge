# __PROJECT__

<!-- Every line here is loaded into EVERY session, and is re-injected from disk
     after /compact. The test for keeping a line: would removing it cause a
     mistake? If not, delete it.

     Anthropic's guidance is "under 200 lines... longer files consume more
     context and reduce adherence" (code.claude.com/docs/en/best-practices).
     Aim far lower here — under 25 — because this file is concatenated with
     ~/.claude/CLAUDE.md and paid for in every session.

     File-specific guidance can go in .claude/rules/*.md with `paths:`
     frontmatter, which loads only when a matching file is read. Caveat worth
     knowing: path-scoped rules are LOST after /compact until a matching file
     is read again, so never put anything load-bearing there. Load-bearing
     means a hook. -->

## What this is

__DESCRIPTION__

## Commands you cannot guess

<!-- Only unguessable ones. Everything runnable is declared as an entry point,
     so `uv run` with no arguments lists them - that is the single entry
     point, and nothing here is invoked by file path. -->

## Deviations from defaults

<!-- Where this project does something a competent Python dev would not expect. -->

## Gotchas

<!-- Traps that have actually bitten. Add them when they bite, not before. -->

---
Process is enforced by hooks (`.claude/settings.json`), not by this file:
ruff runs on every file you edit; the turn cannot end until ruff, mypy --strict
and the tests are green. Do not restate that here.
