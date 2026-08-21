# Why forge is shaped this way

Rationale and evidence, readable away from the machine. Procedures are in the how-to guides; rules in `kernel/` and `contract/`. Full citations: `kernel/SOURCES.md`.

## The problem

Working with LLMs across projects without a process fails four ways: context accretes until it poisons output; guidance is repeated instead of enforced; quality depends on who is watching; learnings die with the session. forge answers with a small kernel of always-on behaviours, one contract for everything else, and a loop that folds experience back in.

## Kernel and contract, not a feature list

The microkernel pattern: kernel is mechanism, capabilities are policy added on demonstrated need. The contract is the one up-front investment, because contract rework grows superlinearly and feature rework does not. It borrows the manifest-plus-lazy-activation shape that Eclipse, VS Code, Chrome extensions and Agent Skills converged on, and Meyer's pre/post/invariant triple. The contract is frozen and versioned; kernel internals stay fluid, because anything observable will be depended on.

## The seven behaviours

**Context discipline** is Anthropic's own doctrine on context rot, operationalised: manifests always visible, bodies on trigger, references on demand.

**Plan contract** descends from mission command — intent and end state, not steps — corrected by agent evidence: plans drift during execution, and a bad plan is worse than none.

**Boundaries over instructions** is the distinction between enforced permissions and advisory context. Only architectural constraints give provable properties, and hard boundaries increase usable autonomy. Per-action approval is no substitute: rubber-stamping cannot be trained away.

**Claim-graded evidence** uses the methods that survive testing: two-axis grading, lateral reading, disconfirmation, documented searches, calibrated language, mechanical citation checks. For software, version match and execution beat votes and docs.

**Decision-first interface** uses BLUF, SBAR and Minto's pyramid, with Diátaxis quadrants unmixed. Explanations raise trust without raising discrimination, and humans are poor passive monitors, so reports are rare and substantive.

**Separated verification** is the convergent rule of every serious agentic setup; test quality is the ceiling on autonomy.

**Compounding** follows every working self-improving setup: human-reviewed, git-tracked, periodically deduplicated diffs — never blind accretion.

## The validate capability

Grounded in the strongest causal evidence in entrepreneurship research: a scientific approach — explicit theory, ranked assumptions, pre-registered kill thresholds — makes founders kill bad ideas faster and pivot once. Every test carries a decision rule. Synthetic users are banned as evidence: they fabricate past behaviour and inflate willingness to pay.
