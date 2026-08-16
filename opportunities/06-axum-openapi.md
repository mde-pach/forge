# FastAPI-grade type-driven OpenAPI for Rust/axum

Status: awaiting-judgment · Sweep: 2026-08-16 · Mode: pattern translation (textbook case)

**Gap.** Rust's default web framework has refused first-class OpenAPI for 5 years; three in-repo attempts by maintainers died; every third-party crate reintroduces annotation duplication. The FastAPI property — types as single source of truth, zero duplication — is never reached.

**Evidence.** [axum#50](https://github.com/tokio-rs/axum/issues/50) (2021, E-hard, closed); dead first-party attempts [PR#170](https://github.com/tokio-rs/axum/pull/170), [PR#945](https://github.com/tokio-rs/axum/pull/945), branch openapi-attempt-3 (A2 — maintainers tried and gave up); live 2025-26 ask citing Elysia.js, maintainer: "axum… does not intend to become one" ([#3375](https://github.com/tokio-rs/axum/discussions/3375), A2); utoipa 3.9k stars carrying the duplication tax, 163 open issues (A2).

**Why-now.** Rust API adoption wave + agents consuming OpenAPI clients; Elysia/Hono keep resetting DX expectations.

**Graveyard/tarpit.** The graveyard is instructive, not fatal: attempts died on axum's extractor design erasing type info — the angle must solve that specifically (macro/trait-level route registration) or it joins the pile.

**Shape.** Rust backend teams shipping typed APIs. Real but niche-deep.

**Fit.** Perfect shape (it IS the unchained move on another ecosystem) — but Rust isn't his demonstrated stack; the need is Rust-shaped by definition. Judgment: is learning-depth-in-Rust a cost or an attraction?

**Angle.** Whatever survived the three dead attempts knows where the bodies are buried — read them first. Surface: Rust crate (need-shaped).
