# Cross-session memory/continuity for agent operators

Status: awaiting-judgment · Sweep: 2026-08-16 · Modes: own-friction × incompleteness

**Gap.** Heavy agent operators lose accumulated project understanding at every compaction/session end; each is hand-building the same tiered file-based memory system; the vendor keeps closing the requests.

**Evidence.** Duplicate-ask cluster ≥7 independent issues in anthropics/claude-code, Aug 2025→2026 ([#5619](https://github.com/anthropics/claude-code/issues/5619), [#14227 — closed not-planned](https://github.com/anthropics/claude-code/issues/14227), [#34556 — operator documents 59 compactions/26 days + full self-built 3-tier memory](https://github.com/anthropics/claude-code/issues/34556); A2 cluster, magnitude B3 — reaction counts unretrievable). **Own-friction:** forge exists because "learnings die with each session" (docs/explanation.md); nrs (Apr 2026) is a prior attempt at context discipline.

**Why-now.** Session lengths exploded 2025-26; compaction became the daily ceiling; all issue volume within 12 months.

**Graveyard/tarpit.** CLAUDE.md (static), vendor memory tools (not wired into Code sessions — the exact complaint), MCP memory servers/mem0/Letta (retrieval noise, not compaction-aware), young plugins. Survives because it needs session-lifecycle literacy; vendor declined. Risk: vendor ships it eventually — the classic platform-gap squeeze. That risk is the judgment question.

**Shape.** Full-time operators (12-18h/day), small labs, $100–200/mo subscribers articulating price-vs-amnesia. Intense, reachable (they file issues), growing.

**Fit.** High — forge's own thesis productized; maxime is the user.

**Angle.** forge's loop/frictions/kernel discipline generalized into an installable product rather than a personal framework. Surface: agnostic (files + hooks).
