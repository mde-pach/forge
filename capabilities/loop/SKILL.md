---
name: loop
description: Fold session learnings back into forge as reviewed git diffs, and periodically factorize forge itself. Use at the end of substantial work, when an error escaped a boundary, when an instruction repeats, or when a need has no capability.
---

# loop

## Reflect

1. Scan the session for four learning types:
   - **Correction** — the human corrected behavior or output. Candidate: kernel or capability diff.
   - **Escaped error** — something reached runtime/review that a mechanism should have caught. Candidate: new hook, permission, type rule, or verifier — a boundary, never a sentence.
   - **Repeated instruction** — the same guidance given twice. Candidate: boundary or capability; the instruction itself is then deleted, not stored.
   - **Unserved need** — work bent around a missing capability. Candidate: capability proposal scaffolded from `contract/template/`.
2. For each learning, draft the smallest diff against the one right layer. If it fits two places, factorize first.
3. Apply the standing-context test to any diff that adds always-loaded text: *would removing this cause mistakes?* If unclear, prefer a lazy layer (rule, skill, reference).
4. Present all diffs in one SBAR brief: what happened, what each diff changes, expected effect, ask (approve / reject / edit each).
5. Commit approved diffs individually, message stating the learning that motivated it. Rejected diffs are recorded in the brief only — rejection reasons are themselves signals.

## Factorize (periodic)

1. Measure standing context (everything always loaded, per surface). Compare to last pass.
2. Hunt duplicates across kernel, rules, skills; merge to one location, reference from others.
3. List capabilities whose `need` hasn't occurred since the last pass; propose deprecation.
4. Delete nothing outside the contract's lifecycle rules.
5. Report net size delta. Growth = failed pass; explain or revert.

## Verification

The human reviews every diff (nothing self-applies). Factorization is graded by net context size.

## Report

SBAR brief per reflect; size-delta report per factorize. Durable state: git history is the log — no separate ledger.
