---
name: validate
description: Evaluate a product or feature idea against real evidence with pre-registered kill thresholds. Use before building anything intended to be sold, or when deciding whether to continue a bet.
---

# validate

## 1. Theory before tests

Write the hypothesis: *we help X do Y by doing Z*. List assumptions; rank by (impact if wrong × uncertainty). For the top assumption, pre-register the test and its kill/continue threshold **before** gathering evidence. No threshold, no test.

## 2. Structured scan (cheapest evidence first)

- **Origin check**: is the idea organic (a problem the builder actually has/observed) or made-up? Made-up ideas need disproportionately stronger evidence.
- **Graveyard/competitor scan**: search for prior attempts, living and dead. Competition validates the problem space; a graveyard of near-clones with no structural "why now" is a tarpit — default verdict no.
- **Why-now**: name the recent change (tech, regulation, behavior) that makes this newly possible. Absent → downgrade.
- **Well-shape**: identify the small group with intense need and a plausible expansion path. Bottom-up sizing only: reachable accounts × realistic price × realistic conversion through one named channel. Top-down TAM is never a go signal.

## 3. Escalating commitment ladder

Advance only while thresholds pass; each rung is a pre-registered test:

1. Real-signal collection — community complaints, forum threads, interview material (Mom Test hygiene below)
2. Landing page with a real pricing page — clicks on paid plans are the metric, signups are weak evidence
3. Concierge / manual delivery to a handful of real users
4. Presale — money is the strongest evidence

## 4. Evidence hygiene

- Grade every item: source reliability × credibility, independently; trace to origin; discount copies.
- Mom Test rules on any human input: past specific behavior only; flag and discount compliments, hypotheticals, and unsolicited feature ideas; score conversations by commitment extracted (time, reputation, money).
- LLM simulation (personas, synthetic interviews, WTP guesses) is a pre-filter and prep tool only — always labeled `unvalidated-synthetic`, never in the evidence table.

## 5. Decide

At each threshold: **persevere / pivot / kill** — explicitly, against the pre-registered rule. One focused pivot beats serial pivoting. If tests keep passing weakly, that is a decision point too — diminishing returns are real; more testing is not the safe default.

## Verification

Evidence audit: every claim in the final recommendation must trace to a graded artifact. Any claim that traces only to model output fails the audit.

## Report

SBAR per gate: hypothesis state, evidence table (graded), assessment against threshold, recommendation. Durable state: one `validation/<idea>.md` per idea in the project, appended per test — the full decision log.

Method rationale and evidence: `references/methods.md`.
