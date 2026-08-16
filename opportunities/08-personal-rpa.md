# Personal RPA — scheduled agents for apps with no API

Status: awaiting-judgment · Sweep: 2026-08-16 · Mode: new-primitive

**Gap.** Decade-old, well-documented desire: automate the vendor portal / web app that never shipped an API. Scripted RPA was brittle; a vision+DOM agent that self-heals changes the economics for solo operators.

**Evidence.** Desire predating primitive: [HN 2019](https://news.ycombinator.com/item?id=20257768), [HN 2020](https://news.ycombinator.com/item?id=23141002), [HN 2022](https://news.ycombinator.com/item?id=31518601) (B3 each, independent); primitive: Chrome DevTools MCP public preview Sept 2025 ([Osmani](https://addyosmani.com/blog/devtools-mcp/), B2) atop MCP registry standardization (A2).

**Why-now.** Strong and fresh.

**Graveyard/tarpit.** UiPath-class incumbents ignore the low end; Zapier stops at APIs. Adjacent agent-browser space is heavily funded/crowded — differentiation must be the solo-operator shape (cron + audit trail + failure alerts), not the browser driving itself.

**Shape.** Solo bookkeepers, small agencies pulling client reports, <10-person ops teams. Pays for time saved; not developer-shaped customers (support burden differs from his usual audience).

**Fit.** Moderate — the need is real and the shape sellable, but it's outside his demonstrated veins (non-dev customers, hosted browser infra to operate).

**Angle.** Plain-English recorded intents, persistent authenticated profiles, screenshot audit trail. Surface: hosted service (the need demands operations, not a lib).
