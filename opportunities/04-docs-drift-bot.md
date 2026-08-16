# Docs drift bot — self-maintaining documentation in CI

Status: awaiting-judgment · Sweep: 2026-08-16 · Modes: new-primitive × own-adjacent

**Gap.** Docs rot the moment code moves; "always-up-to-date documentation" is a named holy grail; agents in CI + a versioned procedure format (Skills) finally make a docs-drift PR bot buildable.

**Evidence.** JetBrains names the holy grail ([2022](https://blog.jetbrains.com/writerside/2022/01/the-holy-grail-of-always-up-to-date-documentation/), B2); "Confluence is where documentation goes to die" ([dev.to](https://dev.to/niklasbegley/confluence-is-where-documentation-goes-to-die-3ank), C3); SO survey: docs = #1 toil candidate for AI ([2024](https://stackoverflow.blog/2024/12/19/developers-hate-documentation-ai-generated-toil-work/), B2); GitHub ships a cookbook for the pattern ([docs](https://docs.github.com/en/enterprise-cloud@latest/copilot/tutorials/copilot-chat-cookbook/documenting-code/syncing-documentation-with-code-changes), A2 — also a competition signal).

**Why-now.** Agent Skills (Oct 2025) as the doc-convention carrier; agents-in-CI mundane; token economics allow whole-repo passes.

**Graveyard/tarpit.** No graveyard — pre-consolidation. Competition risk is platform-native (GitHub Copilot could absorb it). Differentiator would be opinionated doc quality (Diátaxis conformance, verified claims) vs generic sync.

**Shape.** 1-writer dev-tool companies, solo OSS maintainers, agencies handing off documented projects. Pays per-repo.

**Fit.** High conceptual fit (his docs discipline is exactly the encoded convention); but it's a service/product to operate, not a glue lib.

**Angle.** The bot doesn't write docs — it enforces a documented standard (Diátaxis quadrants, claim verification) and opens fix PRs. Surface: GitHub Action + Skill.
