# __PROJECT__

__DESCRIPTION__

```bash
npm install
npm run dev            # Turbopack (does NOT type-check)
npm run typecheck      # tsc --noEmit - the type check Turbopack skips
npm run check          # biome: format + lint + import sort, writes fixes
docker compose up --build
```

Quality gates run automatically inside Claude Code sessions (see `.claude/`).
