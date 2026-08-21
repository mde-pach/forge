---
name: prospect
description: Autonomously hunt for potential projects — missing bricks, incomplete implementations, and untranslated patterns in ecosystems — and bring them as evidence-graded opportunity records for the owner's judgment. Use for "find what to build", opportunity sweeps, or when a friction keeps repeating.
---

# prospect

Prospect finds and grades; it never decides. Survivors of the owner's judgment enter `validate`.

## 1. Define the grounds

Grounds are need-domains ("knowledge/docs workflows", "API glue and DX"), plus
sources and a time window — never stacks; the stack follows the need at build
time. Record the protocol (domains, sources, queries) with the results.

## 2. Hunt — four modes

- **Own-friction mining**: the owner's frictions (in forge-state), project logs
  and corrections, for pain that repeated. Strongest signal.
- **Pattern translation**: a pattern loved in ecosystem A and absent in B, with
  a reason the translation is newly feasible or unattempted. If B has a
  graveyard, learn why before proposing.
- **Incompleteness scan**: projects with traction whose users keep asking for
  the same missing piece — issues, reactions, stale PRs, forks patching one gap.
- **New-primitive watch**: releases that newly enable old desires. A desire
  just unblocked outranks one merely unserved.

## 3. Record — one per candidate

The gap in one sentence. Evidence, each item graded (source reliability ×
credibility) and linked to the real artifact. The why-now, or "none found",
which is a downgrade. The graveyard check. The shape: who has the pain
intensely, how many are reachable. The fit note against the owner's tastes —
glue layers, DX, git-native tools, lateral moves over recreating a category.
The implementation angle if visible, and the surface the need implies.

## 4. Deliver

One SBAR brief per sweep: grounds, protocol, candidates ranked (evidence ×
why-now × fit), records attached, and the ask: which go to judgment.

## Autonomy

Invoked, never self-scheduled. A sweep is read-only research; the gate is the
owner's judgment. Nothing is built from a sweep alone.

## Verification

Evidence audit: every signal resolves to a linked real artifact. A record whose
evidence is only the sweep's reasoning fails.

## Report

SBAR per sweep. One file per candidate in the owner's private data store, never
in a framework repo. Judged-out records are marked, not deleted.

Method rationale: `references/methods.md`.
