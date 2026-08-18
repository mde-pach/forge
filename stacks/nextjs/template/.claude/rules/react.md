---
paths:
  - "src/**/*.tsx"
  - "src/**/*.ts"
---

# App Router conventions

<!-- Loaded only when a source file is read. Keep it to what the type system
     and biome cannot express. -->

- Server Components by default; add `"use client"` only when the component
  needs state, effects or browser APIs, and push it as far down the tree as possible.
- Data fetching happens in Server Components or route handlers, never in effects.
- `noUncheckedIndexedAccess` is on: indexing an array yields `T | undefined`.
  Handle it; do not reach for `!`.
