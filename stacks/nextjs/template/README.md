# __PROJECT__

__DESCRIPTION__

```bash
bun install
bun run dev      # Turbopack (does NOT type-check)
bun run check    # biome + tsc --noEmit + next build — the same gate the hook runs
bun run fix      # biome, writing fixes
bun run build
```

Everything runnable is declared in `package.json`; `bun run` with no arguments
lists them. Nothing here is invoked by file path.

## What enforces quality

| When | What runs |
|---|---|
| after each edit | biome on that file — blocks on failure |
| when the turn ends | `bun run check` — the turn cannot end until it is green |
| push and PR | the same check, plus a docker build |

Turbopack does not type-check, so `tsc --noEmit` is a separate mandatory step
rather than something `next dev` covers.
