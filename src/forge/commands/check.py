"""
Every check forge makes about itself.

Each check is paired with a *proof that it works*: a deliberate break that the
check must notice. An assertion nobody has ever seen fail is not evidence -
two of the monitor's checks passed while testing nothing, and generated test
suites reaching 100% line coverage have been measured catching 4% of injected
faults. Coverage is not detection.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence

from forge.checks import documented_commands, handlers, manifests, orphans
from forge.registry import REGISTRY, ROOT, roles


def _proofs() -> list[tuple[str, bool, str]]:
    """Break something on purpose; the check must notice. Name, passed, detail."""
    out: list[tuple[str, bool, str]] = []

    # The name is assembled rather than written, because this file is a
    # liveness root: a literal path here would reference the planted file and
    # make it live, so the proof would quietly stop proving anything. That is
    # the second time this exact trap has fired - the orphan checker's own
    # docstring did it first.
    planted = "plugins/forge-monitor/__planted" + "_orphan.sh"
    found, _ = orphans.find([*orphans.tracked(), planted])
    out.append(
        (
            "orphan detection notices a planted file",
            planted in found,
            "a file referenced by nothing must be reported",
        )
    )

    dup_rejected = False
    try:
        from forge.registry import Entry, _validate

        original = REGISTRY
        import forge.registry as reg

        reg.REGISTRY = (*original, Entry("dup", original[0].role, "x", "x:y"))
        try:
            _validate()
        except ValueError:
            dup_rejected = True
        finally:
            reg.REGISTRY = original
    except Exception:  # noqa: BLE001
        dup_rejected = False
    out.append(
        (
            "the registry rejects two entries with one role",
            dup_rejected,
            "cardinality is the mechanism that stops a second install path",
        )
    )

    import forge.registry as reg
    from forge.registry import Entry

    original = reg.REGISTRY
    try:
        reg.REGISTRY = (*original, Entry("ghost", "ghost-role", "x", "forge.commands.nothing:run"))
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

    doc = ROOT / "stacks/nextjs/template/README.md"
    original = doc.read_text()
    try:
        doc.write_text(original + "\nbun run __not_a_real_script\n")
        caught = any("__not_a_real_script" in e for e in documented_commands.check())
    finally:
        doc.write_text(original)
    out.append(
        (
            "a document naming a command that does not exist is caught",
            caught,
            "prose has no compiler; this is the smallest thing that gives it one",
        )
    )
    return out


def run(_args: Sequence[str] = ()) -> int:
    failures = 0

    print("registry")
    print(f"  ok    {len(REGISTRY)} commands, {len(roles())} distinct roles")

    handler_errs = handlers.check()
    if handler_errs:
        failures += len(handler_errs)
        for e in handler_errs:
            print(f"  FAIL  {e}")
    else:
        print("  ok    every declared command resolves to a callable")

    print("capability manifests")
    errs = manifests.check()
    if errs:
        failures += len(errs)
        for e in errs:
            print(f"  FAIL  {e}")
    else:
        print("  ok    every capability manifest matches the contract")

    print("documented commands")
    doc_errs = documented_commands.check()
    if doc_errs:
        failures += len(doc_errs)
        for e in doc_errs:
            print(f"  FAIL  {e}")
    else:
        print("  ok    every command a document tells you to run is declared")

    print("reachability")
    orphaned, described = orphans.find()
    uncited = orphans.uncited_references()
    for f in orphaned:
        print(f"  FAIL  {f} is referenced by nothing")
    for f in described:
        print(f"  FAIL  {f} is described in prose but nothing runs it")
    for f in uncited:
        print(f"  FAIL  {f} is not cited by its own SKILL.md")
    failures += len(orphaned) + len(described) + len(uncited)
    if not (orphaned or described or uncited):
        print("  ok    every tracked file is reachable from something that runs")

    print("plugin behaviour")
    verifier = ROOT / "plugins" / "forge-monitor" / "verify.sh"
    if shutil.which("bash") and verifier.is_file():
        r = subprocess.run(["bash", str(verifier)], capture_output=True, text=True, check=False)
        tail = (r.stdout or "").strip().splitlines()
        summary = tail[-1] if tail else "no output"
        if r.returncode == 0:
            print(f"  ok    the session monitor: {summary}")
        else:
            failures += 1
            print(f"  FAIL  the session monitor: {summary}")
            for line in tail:
                if "FAIL" in line:
                    print(f"        {line.strip()}")
    else:
        failures += 1
        print("  FAIL  the session monitor's verifier is missing")

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
