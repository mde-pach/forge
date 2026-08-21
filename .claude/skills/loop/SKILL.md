---
name: loop
description: Fold session learnings back into forge as reviewed git diffs, and periodically factorize forge itself. Use at the end of substantial work, when an error escaped a boundary, when an instruction repeats, or when a need has no capability.
---

# loop

## Reflect

1. Scan the session for four learning types: a **correction** by the human
   (candidate: kernel or capability diff); an **escaped error** a mechanism
   should have caught (candidate: a boundary, never a sentence); a **repeated
   instruction** (candidate: boundary or capability, then delete the
   instruction); an **unserved need** (candidate: capability scaffolded from
   `contract/template/`).
2. For each, draft the smallest diff against the one right layer. If it fits two
   places, factorize first.
3. Any diff that adds always-loaded text passes the test: would removing this
   cause mistakes? If unclear, prefer a lazy layer.
4. Present all diffs in one SBAR brief: what happened, what each diff changes,
   expected effect, ask (approve / reject / edit each).
5. Commit approved diffs individually, message stating the learning. Rejections
   are recorded in the brief only.

## Factorize (periodic)

1. Measure standing context per surface; compare to the last pass.
2. Merge duplicates across kernel, rules and skills to one location.
3. Propose deprecation for capabilities whose `need` has not occurred.
4. Delete nothing outside the contract's lifecycle.
5. Report the net size delta. Growth is a failed pass.

## Verification

The human reviews every diff. Factorization is graded by net context size.

## Report

SBAR brief per reflect; size-delta report per factorize. Git history is the log.
