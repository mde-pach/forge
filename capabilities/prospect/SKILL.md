---
name: prospect
description: Autonomously hunt for potential projects — missing bricks, incomplete implementations, and untranslated patterns in ecosystems — and bring them as evidence-graded opportunity records for the owner's judgment. Use for "find what to build", opportunity sweeps, or when a friction keeps repeating.
---

# prospect

Prospect feeds judgment; judgment feeds validate. This capability never decides — it finds and grades.

## 1. Define the grounds — need-first

Grounds are **need-domains**: territories where a kind of unmet need surfaces (e.g. "knowledge/docs workflows", "API glue and DX", "content publishing") plus the sources to sweep and a time window. Grounds are never stacks — the stack is a consequence of the need, decided at build time (a git-based wiki could be built in anything). Record the protocol (domains + sources + queries) alongside the results.

## 2. Hunt — four modes, run any or all

- **Own-friction mining** (strongest signal — organic ideas beat invented ones): sweep the owner's FRICTIONS.md files, project logs, recent experiments and corrections for pain that repeated. A dissatisfaction strong enough to build around is a candidate (pattern: wiki hosting dissatisfied → noCMS).
- **Pattern translation**: a pattern developers demonstrably love in ecosystem A, absent in ecosystem B (pattern: FastAPI's DX → Django = unchained). Evidence that A's pattern is loved AND B lacks it, plus a reason the translation is newly feasible or simply unattempted — if B has a graveyard of attempts, find out why they died before proposing.
- **Incompleteness scan**: projects with real traction whose users keep asking for the same missing piece — issue trackers ("is there a way to…", feature requests with reactions, stale PRs), forks that all patch the same gap, plugin ecosystems papering over a core absence. The persistent delta IS the candidate.
- **New-primitive watch**: releases and platform capabilities that newly enable old desires — the structural why-now generator. A desire that was blocked and just got unblocked outranks a merely unserved one.

## 3. Record — one opportunity record per candidate

Each record contains: the gap in one sentence; the evidence, each item graded (source reliability × item credibility, linked to the real artifact); the why-now (or explicit "none found" — that is a downgrade, not a footnote); the graveyard/tarpit check (prior attempts, living and dead, and why they landed where they did); the shape (well-shape: who has this pain intensely, roughly how many are reachable); the fit note (does it match the owner's demonstrated tastes and leverage — glue layers, DX, git-native tools); the implementation angle if one is visible — the clever twist that makes it possible; and, as an output only, the implementation surface the need implies (a Python lib if the need is Python-shaped, TS if TS-shaped, anything if agnostic).

## 4. Deliver — judgment brief

One SBAR brief per sweep: grounds covered, protocol used, candidates ranked (evidence strength × why-now × fit), each record attached, and the ask: which candidates go to a judgment discussion. Survivors of judgment enter validate with their record as the starting evidence table.

## Autonomy

Prospect is invoked, never self-scheduled. While running, a sweep is read-only research and needs no gate. The gate is judgment, and it is always the owner's. Nothing advances to validate, and nothing gets built, from a sweep alone.

## Verification

Evidence audit: every signal in every record resolves to a linked real artifact. A record whose evidence is only the sweep's own reasoning fails.

## Report

SBAR per sweep. Durable state: one file per candidate in the owner-designated private data store — NEVER in a framework repo (output separation, contract convention). Until a store is designated: session workspace + files delivered to the owner. Judged-out records are marked, not deleted — rejections are calibration data.

Method rationale and evidence: `references/methods.md`.
