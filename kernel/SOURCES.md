# Sources — evidence base for the kernel

For humans maintaining forge. Never projected into sessions.

## Behavior 1 — Context discipline
- Anthropic, Effective context engineering for AI agents (context rot, attention budget, just-in-time retrieval): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Claude Code best practices ("would removing this cause mistakes?", <200-line CLAUDE.md): https://code.claude.com/docs/en/best-practices
- Agent Skills three-layer progressive disclosure: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- On-demand discovery measured (150k→2k tokens): https://www.anthropic.com/engineering/code-execution-with-mcp

## Behavior 2 — Plan contract
- Mission command / commander's intent (ADP 6-0): https://www.army.mil/article/106872/understanding_mission_command
- Plan drift measured; re-grounding mitigation; bad plan < no plan: https://arxiv.org/html/2604.12147v1
- Plan-approval architecture in production (HULA, Atlassian): https://arxiv.org/abs/2411.12924
- Delegation needs engaged principal (MBO meta-analysis): Rodgers & Hunter 1991, J. Applied Psychology 76(2)
- Gate on reversibility × stakes: https://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf ; https://www.anthropic.com/news/our-framework-for-developing-safe-and-trustworthy-agents

## Behavior 3 — Boundaries over instructions
- Enforced rules vs advisory context: https://code.claude.com/docs/en/permissions
- Hard boundaries increase autonomy (84% fewer prompts): https://www.anthropic.com/engineering/claude-code-sandboxing
- Provable control-flow integrity via plan-then-execute: https://arxiv.org/abs/2506.08837
- Lethal trifecta: https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/

## Behavior 4 — Claim-graded evidence
- Two-axis grading (Admiralty, NATO AJP-2.1); GRADE handbook: https://gdt.gradepro.org/app/handbook/handbook.html
- Lateral reading beats on-page evaluation: Wineburg & McGrew 2019, https://journals.sagepub.com/doi/10.1177/016146811912101102
- Checklist (CRAAP) underperformance: https://files.eric.ed.gov/fulltext/EJ1329588.pdf
- SIFT / trace to origin: https://hapgood.us/2019/06/19/sift-the-four-moves/
- ACH, diagnosticity, disconfirmation (Heuer): https://www.crest-approved.org/wp-content/uploads/2022/04/Psychology-of-Intelligence-Analysis-1.pdf
- SO answers ~31% API misuse; votes uncorrelated: ExampleCheck ICSE 2018. Security votes anti-predict: Chen et al. ICSE 2019. 58% of obsolete answers stale day one: https://arxiv.org/pdf/1903.12282
- Official docs empirically flawed: Aghajani ICSE 2020
- Documented search (PRISMA 2020): https://www.prisma-statement.org/prisma-2020-statement
- Calibrated language (ICD 203; Kent): https://www.intel.gov/assets/documents/intelligence-community-directives/ICD_203.pdf
- Citation verification necessity (RAG 17–33% hallucination; AI search >60% misattribution): https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf ; https://www.cjr.org/tow_center/we-compared-eight-ai-search-engines-theyre-all-bad-at-citing-news.php

## Behavior 5 — Decision-first human interface
- BLUF (AR 25-50); SBAR clinical evidence; Minto pyramid (McKinsey)
- Explanations raise trust without raising discrimination: Buçinca et al. 2021, https://dl.acm.org/doi/10.1145/3449287
- Humans are poor passive monitors: Bainbridge 1983, Ironies of Automation
- Diátaxis: https://diataxis.fr/

## Behavior 6 — Separated verification
- Worker never grades itself; verification ladder: https://code.claude.com/docs/en/best-practices
- Test quality is the autonomy ceiling: https://www.anthropic.com/engineering/building-c-compiler

## Behavior 7 — Compounding
- Skills co-development / capture learnings: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Reviewed-diff consensus across self-improving setups (claude-reflect et al.); compounding engineering: https://every.to/c/compounding-engineering

## Structure (kernel + contract)
- Microkernel pattern: Richards, Software Architecture Patterns; POSA vol. 1
- Contract not YAGNI-able: https://martinfowler.com/bliki/Yagni.html ; Boehm rework curves, Making Software ch.10
- Design by Contract: Meyer, IEEE Computer 1992
- API evolution algebra; deprecate don't delete: https://wiki.eclipse.org/Evolving_Java-based_APIs
- Two-tier stability: https://www.kernel.org/doc/Documentation/process/stable-api-nonsense.rst
- Manifest + lazy activation convergence: Eclipse, VS Code, Chrome MV3, Agent Skills
- Hyrum's Law: https://www.hyrumslaw.com/ ; SemVer: https://semver.org/
- Loud failure, uniform conventions (Unix critique): http://harmful.cat-v.org/cat-v/
- Paved road / support asymmetry: Rails Doctrine; Netflix full-cycle; Spotify golden path
- Conway / Team Topologies applied to human+sessions: https://www.melconway.com/Home/Committees_Paper.html

## Validate capability
- Scientific-approach RCTs (759 firms; faster kills, single pivot): Camuffo et al., SMJ 2024
- Testing has diminishing returns: Ladd, HBR 2016
- Mom Test: https://www.momtestbook.com/
- Opportunity solution trees: https://www.producttalk.org/opportunity-solution-tree/
- Buffer WTP ladder: https://buffer.com/resources/idea-to-paying-customers-in-7-weeks-how-we-did-it/
- YC canon: https://paulgraham.com/startupideas.html ; tarpits (Caldwell)
- Synthetic users unreliable as evidence: https://www.nngroup.com/articles/synthetic-users/ ; WTP inflation 2–3×: MSI Report 25-136
