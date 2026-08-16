# Why forge is shaped this way

Explanation quadrant: rationale and evidence, readable away from the machine. Procedures live in how-to guides; rules live in `kernel/` and `contract/`.

## The problem

Working with LLMs across many projects and surfaces without a process produces four recurring failures: context accretes until it poisons output; guidance gets repeated instead of enforced; work quality depends on who's watching; and learnings die with each session. forge is the standing answer: a small kernel of always-on behaviors, a uniform contract for everything else, and a loop that folds experience back in.

## Kernel + contract, not a feature list

The structure is the microkernel pattern (POSA; Richards): kernel = mechanism, capabilities = policy, added only on demonstrated need. The one deliberate up-front investment is the capability contract — Fowler exempts changeability infrastructure from YAGNI, and Boehm's rework curves show why: contract rework grows superlinearly, feature rework doesn't. The contract borrows the manifest + lazy-activation shape that Eclipse, VS Code, Chrome extensions, and Agent Skills each converged on independently, and Meyer's pre/post/invariant triple with single-owner checks. Stability is two-tier (Linux discipline): the contract is frozen and versioned; kernel internals stay fluid and unexposed, because anything observable will be depended on (Hyrum's Law).

## The seven behaviors, and what they rest on

**Context discipline** is Anthropic's own doctrine since 2025 ("context rot", the per-line test "would removing this cause mistakes?"), operationalized: manifests always visible, bodies on trigger, references on demand — measured to cut token load by orders of magnitude.

**The plan contract** descends from mission command (intent + end state, not step lists — steps go stale) and management-by-objectives, whose meta-analytic lesson is that delegation works only with an engaged principal. Agent-specific evidence adds two corrections: plans measurably drift during execution (mitigation: periodic re-grounding), and a bad plan is worse than no plan — hence plan-quality gates and the off-plan-stops rule.

**Boundaries over instructions** is the production distinction between enforced permissions and advisory context, backed by prompt-injection research showing only architectural constraints give provable properties — and by the sandboxing result that hard boundaries *increase* usable autonomy. Per-action approval is not a substitute: automation-bias research shows rubber-stamping cannot be trained away; the design answer is few, substantive checkpoints.

**Claim-graded evidence** replaces source folklore with the methods that survive testing: two-axis grading (Admiralty), lateral reading (the best-replicated finding in source evaluation — checklists like CRAAP measurably underperform), disconfirmation and diagnosticity (Heuer's ACH), documented searches (PRISMA-lite), calibrated language (ICD 203/Kent), and mechanical citation verification — because even retrieval-grounded systems misground 17–33% of the time. For software: version match and executing the code beat votes and even official docs, both empirically unreliable.

**Decision-first human interface** uses formats with real provenance — BLUF (a military writing regulation), SBAR (clinical outcome evidence), Minto's pyramid — plus Diátaxis's unmixed quadrants. The anti-evidence matters more: explanations raise trust without raising human discrimination, and humans are structurally poor passive monitors, so forge reports rarely and substantively.

**Separated verification** — the producer never grades itself — is the convergent rule of every serious agentic setup, and test quality is the measured ceiling on autonomy.

**Compounding** follows the consensus of every working self-improving setup: learnings as human-reviewed, git-tracked, periodically deduplicated diffs — never blind accretion, which is just context poisoning with good intentions.

## The validate capability

Grounded in the strongest causal evidence in entrepreneurship research: RCTs (759 firms) show a scientific approach — explicit theory, ranked assumptions, pre-registered kill thresholds — makes founders kill bad ideas faster and pivot once, profitably. Over-testing has documented diminishing returns, so every test carries a decision rule. Synthetic users are banned as evidence because they fabricate exactly the data that matters (past behavior) and inflate willingness-to-pay 2–3×.

Full citations: `kernel/SOURCES.md`.
