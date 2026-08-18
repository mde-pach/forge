# __PROJECT__

<!-- Every line here is loaded into EVERY session. The test for keeping a line:
     would removing it cause a mistake? If not, delete it. Target: under 25 lines.
     Anything file-specific belongs in .claude/rules/*.md with `paths:` frontmatter,
     which loads only when a matching file is read. -->

## What this is

__DESCRIPTION__

## Commands you cannot guess

<!-- Only unguessable ones. `npm run dev` is guessable; delete it. -->

## Deviations from defaults

<!-- Where this project does something a competent Next dev would not expect. -->

## Gotchas

<!-- Traps that have actually bitten. Add them when they bite, not before. -->

---
Process is enforced by hooks (`.claude/settings.json`), not by this file:
biome runs on every file you edit; the turn cannot end until `biome ci` and
`tsc --noEmit` are green. Do not restate that here.
