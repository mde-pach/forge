# Regression evals for agent configurations (skills/CLAUDE.md/plugins)

Status: awaiting-judgment · Sweep: 2026-08-16 · Modes: incompleteness (weak ask, strong build signal) × own-friction

**Gap.** People shipping agent configs have no standard way to test "does this skill trigger, help, and did my edit regress it" — ≥4 independent DIY harnesses appeared within ~3 months.

**Evidence.** [cc-plugin-eval](https://github.com/sjnims/cc-plugin-eval) (B2); [Gechev's skill unit tests](https://blog.mgechev.com/2026/02/26/skill-eval/) (B3); two more independent write-ups (C3). Honest caveat from the sweep: building evidence strong, *asking* evidence thin. **Own-friction:** forge's loop needs exactly this to grade its own capability edits; tsty shows his verification taste.

**Why-now.** Skills/plugin marketplaces launched late 2025; configs became shared artifacts needing CI.

**Graveyard/tarpit.** None yet — pre-consolidation; platform absorption risk (Anthropic's plugin-eval is already in early access — direct absorption evidence).

**Shape.** Skill/plugin authors, platform teams standardizing org-wide configs. Small today, grows with the ecosystem.

**Fit.** High (forge would dogfood it), but platform-absorption risk is the judgment question.

**Angle.** Trigger/regression testing as CI for agent configs, vendor-neutral across the emerging skills standard. Surface: agnostic CLI + Action.
