# Async-native typed task queue with FastAPI DX (Python)

Status: awaiting-judgment · Sweep: 2026-08-16 · Modes: own-friction × incompleteness × translation

**Gap.** FastAPI-grade typed async DX ends where background jobs begin: Celery still can't run asyncio tasks (core issue open since **2017**); every challenger drops async, drops types, or grows into a platform.

**Evidence.** [celery#3884](https://github.com/celery/celery/issues/3884) open 9 years, punted to 6.0 (A2); operational resentment continuous 2015→2026 ([HN 2025](https://news.ycombinator.com/item?id=45803765), B3); LLM apps are async I/O pipelines pressing the gap ([practitioner note](https://dangquan1402.github.io/llm-engineering-notes/2026/04/02/lightweight-task-queues-for-llm-apps.html), C4). **Own-friction:** ezq (his repo, Feb 2025) is literally this itch — Postgres-backed simple queue, abandoned at "Steps — TODO".

**Why-now.** LLM workload shift; moderate — the unlock is demand-side, not primitive-side.

**Graveyard/tarpit.** arq maintenance-starved, taskiq closest-but-small, Hatchet/DBOS/Temporal platformizing. Honest caveat from the sweep: the space is actively closing — narrower opening than others.

**Shape.** FastAPI product teams, esp. LLM startups. Large but contested.

**Fit.** Very high (ezq proves the itch; DX-glue taste; Python depth incl. his DI work — lazy-depends parallel resolution would be a differentiator inside a queue).

**Angle.** Postgres-only (no broker), typed tasks as annotated functions, DI-style deps in workers, parallel dependency resolution. Surface: Python lib (need is Python-shaped).
