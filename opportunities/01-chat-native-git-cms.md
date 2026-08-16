# Chat-native git-backed CMS/wiki for mixed teams

Status: awaiting-judgment · Sweep: 2026-08-16 · Modes: own-friction × incompleteness × new-primitive (triple convergence — strongest record)

**Gap.** Teams want their knowledge/content to BE a plain git repo, but every git-backed wiki/CMS forces developer UX; mixed teams stay on Notion/Confluence they resent. The editing side for non-devs — and commenting/async feedback — is the persistent missing piece.

**Evidence.** BookStack refuses git backend since 2018 ([#776](https://github.com/BookStackApp/BookStack/issues/776), A2); Otter Wiki HN launch: praise + recurring WYSIWYG ask ([HN 2024](https://news.ycombinator.com/item?id=41749680), B2); users bolting third-party git sync onto Outline for disaster-recovery ([discussion](https://github.com/outline/outline/discussions/9952), B2); Wiki.js v3 vaporware since 2021, duplicate-ask cluster ([locked discussion](https://github.com/requarks/wiki/discussions/7011), A2); Decap publicly decayed, replacement is bus-factor-1 Sveltia ([Astro maintainers](https://github.com/withastro/docs/discussions/2070), B2); 2018 open-source-ideas ask for exactly "client edits the repo without understanding it" ([#102](https://github.com/open-source-ideas/ideas/issues/102), B2). **Own-friction:** this is maxime's live thesis — wiki-n-go ("Wikipedia-level friction, no account") and noCMS ("the repo is the database"), with the publish-seam still open (noCMS ROADMAP).

**Why-now.** Two unlocks: fine-grained PATs GA (Mar 2025) make a single-repo contents-only credential safe to hand an agent; agents + MCP make "chat edits the repo, commits invisibly" a commodity. And coding agents give repo-resident docs a second consumer — teams are already migrating docs into git for AI retrieval ([HN](https://news.ycombinator.com/item?id=47535363), C3).

**Graveyard/tarpit.** gitit/ikiwiki/Gollum dead or frozen (dev-only UX); Wiki.js stalled; Decap decayed. Each attempt picked one side: git-pure = dev-only editing, editor-grade = database-backed. Space is validated, suppliers keep dying — not a tarpit, an under-supplied vein.

**Shape.** Infra/platform teams self-hosting docs (10–200p, disaster-recovery motive); agencies dreading client handoff; OSS maintainers. Reachable via the exact threads cited.

**Fit.** Maximum — it IS the noCMS/wiki-n-go vein; the sweep externally validates the bet and names the winning delta (non-dev editing + feedback loop).

**Angle.** The un-picked combination: canonical files in git + chat/WYSIWYG editing for non-devs + agent as the invisible git operator. Implementation surface: follows noCMS (TS) — but the need, not the stack, decided that.
