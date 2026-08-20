"""
Every check forge makes about itself.

Two modes, split by cost and by side-effects rather than by taste:

  --fast   read-only, sub-second, no writes. This is what the Stop hook runs on
           every turn, so it must never touch the working tree and must never
           be slow enough to be worth disabling.
  (full)   everything, including the plugin verifier and the proofs. CI runs
           this on a throwaway checkout, where taking ninety seconds and
           writing a file are both fine.

The proofs are the reason the full mode cannot be the hook. `_proofs()` breaks
things on purpose - it appends a bogus command to a template README and asserts
the check notices - and doing that while a session is editing the same tree
races it and leaves the file corrupted if the process dies. They stay in CI.

Each check is paired with such a proof because an assertion nobody has ever
seen fail is not evidence: two of the monitor's checks passed while testing
nothing, and generated suites reaching 100% line coverage have been measured
catching 4% of injected faults. Coverage is not detection.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence

from forge.checks import commands, documented_commands, frictions, handlers, manifests, orphans
from forge.registry import REGISTRY, ROLES, ROOT, roles


def _proofs() -> list[tuple[str, bool, str]]:
    """Break something on purpose; the check must notice. Name, passed, detail."""
    import forge.registry as reg
    from forge.registry import Entry

    out: list[tuple[str, bool, str]] = []

    # The name is assembled rather than written, because this file is a
    # liveness root: a literal path here would reference the planted file and
    # make it live, so the proof would quietly stop proving anything. That is
    # the second time this exact trap has fired - the orphan checker's own
    # docstring did it first.
    planted = "plugins/forge-monitor/__planted" + "_orphan.sh"
    found, _ = orphans.find([*orphans.repo_files(), planted])
    out.append(
        (
            "orphan detection notices a planted file",
            planted in found,
            "a file referenced by nothing must be reported",
        )
    )

    # The inverse, for the derived-filename exemptions: a review file is looked
    # up by recomputing a content hash, a fixture by assembling the event name,
    # so neither can ever be referenced by path - the exemption says that is
    # fine, and this proves the exemption actually exempts. It exists because
    # the .claude/reviews/ entry was added mid-session, unreviewed, with no
    # proof at all - the change was right and the way it happened was wrong.
    for exempt in (".claude/reviews/__planted" + ".md", "plugins/forge-monitor/fixtures/events-__Planted" + ".json"):
        found, _ = orphans.find([*orphans.repo_files(), exempt])
        out.append(
            (
                f"a derived-name file under {exempt.rsplit('/', 1)[0]}/ is not called an orphan",
                exempt not in found,
                "the exemption for filenames that are computed, never written, must hold",
            )
        )

    original = reg.REGISTRY

    def _rejects(entry: Entry) -> bool:
        try:
            reg.REGISTRY = (*original, entry)
            try:
                reg.validate()
            except ValueError:
                return True
            return False
        finally:
            reg.REGISTRY = original

    out.append(
        (
            "the registry rejects two entries with one role",
            _rejects(Entry("dup", original[0].role, "x", "x:y")),
            "cardinality is what stops a second mechanism for a job that has one",
        )
    )
    out.append(
        (
            "the registry rejects a role that is not in ROLES",
            _rejects(Entry("invented", "a-brand-new-job", "x", "x:y")),
            (
                "uniqueness alone is free to satisfy - you just type a new role beside "
                "the new command, which is exactly how forge reached seven"
            ),
        )
    )

    try:
        reg.REGISTRY = (*original, Entry("ghost", ROLES[0], "x", "forge.commands.nothing:run"))
        ghost_caught = any("does not import" in e for e in handlers.check())
    finally:
        reg.REGISTRY = original
    out.append(
        (
            "a declared command whose handler does not exist is caught",
            ghost_caught,
            "the registry promised `forge docs` for an hour before the module existed",
        )
    )

    # A command nothing calls. `__uncalled` appears in no workflow, hook or
    # how-to, which is the whole point.
    try:
        reg.REGISTRY = (*original, Entry("__uncalled", ROLES[0], "x", "forge.commands.check:run"))
        uncalled_caught = any("__uncalled" in e for e in commands.check())
    finally:
        reg.REGISTRY = original
    out.append(
        (
            "a declared command that nothing invokes is caught",
            uncalled_caught,
            "three of seven commands had no caller while the registry reported ok",
        )
    )

    # Both friction proofs write to the tree, which is why they live here and
    # not in the fast half the Stop hook runs.
    fr = ROOT / "FRICTIONS.md"
    before_fr = fr.read_text()
    try:
        fr.write_text(before_fr + "| 999 | 2026-01-01 | planted | closed by nothing |\n")
        closed_caught = any("999" in e and "still here" in e for e in frictions.check())
    finally:
        fr.write_text(before_fr)
    out.append(
        (
            "a friction marked closed and left in the file is caught",
            closed_caught,
            "the table reached 75 rows, 50 of them closed, because the policy was prose",
        )
    )

    guinea = ROOT / "docs/how-to/docs.md"
    before_g = guinea.read_text()
    # Assembled, not written out: spelled in full here, the citation would be a
    # real one, pointing at a row that does not exist - so the proof reported
    # ITSELF and the check went red on a clean tree. It then did it a second
    # time, in the comment explaining the first. Third and fourth outing for
    # this trap overall: the orphan checker's
    # docstring resurrected the file it named, and the planted-orphan proof did
    # it again. A checker must not contain the thing it looks for.
    marker = "friction " + "998"
    try:
        guinea.write_text(f"{before_g}\nSee {marker} for why.\n")
        dangling_caught = any("998" in e for e in frictions.check())
    finally:
        guinea.write_text(before_g)
    out.append(
        (
            "a citation of a friction that no longer exists is caught",
            dangling_caught,
            "removing closed rows breaks whatever pointed at them, silently",
        )
    )

    # The regression that made the two proofs above worthless for one commit:
    # the file list was `git ls-files`, so a file that existed but had not been
    # staged was invisible to every check built on it.
    unstaged = ROOT / ("__unstaged" + "_probe.md")
    try:
        unstaged.write_text("probe\n")
        sees_unstaged = str(unstaged.relative_to(ROOT)) in orphans.repo_files()
    finally:
        unstaged.unlink(missing_ok=True)
    out.append(
        (
            "a file that exists but has not been staged is still checked",
            sees_unstaged,
            "new code is where new defects are, and the Stop hook runs before anyone stages it",
        )
    )

    doc = ROOT / "stacks/nextjs/template/README.md"
    before = doc.read_text()
    try:
        doc.write_text(before + "\nbun run __not_a_real_script\n")
        caught = any("__not_a_real_script" in e for e in documented_commands.check())
    finally:
        doc.write_text(before)
    out.append(
        (
            "a document naming a command that does not exist is caught",
            caught,
            "prose has no compiler; this is the smallest thing that gives it one",
        )
    )
    return out


def fast() -> tuple[int, list[str]]:
    """Read-only checks. Returns (failures, lines). Writes nothing, anywhere."""
    lines: list[str] = []
    failures = 0

    def report(title: str, errs: list[str], ok: str) -> None:
        nonlocal failures
        lines.append(title)
        if errs:
            failures += len(errs)
            lines.extend(f"  FAIL  {e}" for e in errs)
        else:
            lines.append(f"  ok    {ok}")

    lines.append("registry")
    lines.append(f"  ok    {len(REGISTRY)} commands, {len(roles())} of {len(ROLES)} roles filled")
    handler_errs = handlers.check()
    if handler_errs:
        failures += len(handler_errs)
        lines.extend(f"  FAIL  {e}" for e in handler_errs)
    else:
        lines.append("  ok    every declared command resolves to a callable")

    report(
        "command call sites",
        commands.check(),
        "every declared command is invoked by something outside the registry",
    )
    report(
        "capability manifests",
        manifests.check(),
        "every capability manifest matches the contract",
    )
    report(
        "documented commands",
        documented_commands.check(),
        "every command a document tells you to run is declared",
    )

    report(
        "frictions",
        frictions.check(),
        f"{len(frictions.rows())} open, none marked closed, every citation resolves",
    )

    orphaned, described = orphans.find()
    uncited = orphans.uncited_references()
    reach = (
        [f"{f} is referenced by nothing" for f in orphaned]
        + [f"{f} is described in prose but nothing runs it" for f in described]
        + [f"{f} is not cited by its own SKILL.md" for f in uncited]
    )
    report("reachability", reach, "every file in the repo is reachable from something that runs")
    return failures, lines


def run(args: Sequence[str] = ()) -> int:
    fast_only = "--fast" in args
    failures, lines = fast()
    print("\n".join(lines))

    if fast_only:
        print()
        print("clean" if failures == 0 else f"{failures} problem(s)")
        return 1 if failures else 0

    print("plugin behaviour")
    # Every plugin's verifier, found by convention rather than named: naming
    # one here is how forge-guard shipped with no check at all - the hardcoded
    # path ran the monitor's verifier and nothing noticed the guard had none.
    verifiers = sorted((ROOT / "plugins").glob("*/verify.sh"))
    if not shutil.which("bash"):
        # Fail, and run nothing: the loop below would raise FileNotFoundError
        # mid-report. Review caught this refactor keeping the message and
        # losing the pre-change guard around the execution.
        failures += 1
        print("  FAIL  bash is missing; no plugin verifier can run")
        verifiers = []
    elif not verifiers:
        failures += 1
        print("  FAIL  no plugin ships a verifier")
    for verifier in verifiers:
        name = verifier.parent.name
        r = subprocess.run(["bash", str(verifier)], capture_output=True, text=True, check=False)
        tail = (r.stdout or "").strip().splitlines()
        summary = tail[-1] if tail else "no output"
        if r.returncode == 0:
            print(f"  ok    {name}: {summary}")
        else:
            failures += 1
            print(f"  FAIL  {name}: {summary}")
            for line in tail:
                if "FAIL" in line:
                    print(f"        {line.strip()}")
    for plugin in sorted(p.parent.name for p in (ROOT / "plugins").glob("*/.claude-plugin")):
        if not (ROOT / "plugins" / plugin / "verify.sh").is_file():
            failures += 1
            print(f"  FAIL  plugin {plugin} ships no verifier - its behaviour is checked by nothing")

    print("the checks themselves")
    for name, passed, why in _proofs():
        if passed:
            print(f"  ok    {name}")
        else:
            failures += 1
            print(f"  FAIL  {name} — {why}")

    print()
    print("clean" if failures == 0 else f"{failures} problem(s)")
    return 1 if failures else 0
