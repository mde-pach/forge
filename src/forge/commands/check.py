"""Every check forge makes about itself.

`--fast` is read-only and sub-second; the Stop hook runs it on every turn.
The full run adds the plugin verifiers and the test suite, which write to
temporary directories and take longer; CI runs it.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Sequence

from forge.checks import (
    commands,
    density,
    documented_commands,
    handlers,
    hook_parity,
    manifests,
    orphans,
)
from forge.registry import REGISTRY, ROLES, ROOT, roles


def fast() -> tuple[int, list[str]]:
    """Returns (failures, report lines). Writes nothing."""
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
    report("handlers", handlers.check(), "every declared command resolves to a callable")
    report("command call sites", commands.check(), "every declared command is invoked by something")
    report("capability manifests", manifests.check(), "every manifest matches the contract")
    report(
        "documented commands", documented_commands.check(), "every documented command is declared"
    )
    report(
        "hook parity",
        hook_parity.check() + hook_parity.drift(),
        "settings fire what the manifests declare",
    )

    lines.append("prose density")
    lines.extend(density.gauge())

    orphaned, described = orphans.find()
    uncited = orphans.uncited_references()
    report(
        "reachability",
        [f"{f} is referenced by nothing" for f in orphaned]
        + [f"{f} is described in prose but nothing runs it" for f in described]
        + [f"{f} is not cited by its own SKILL.md" for f in uncited],
        "every file is reachable from something that runs",
    )
    return failures, lines


def _plugin_verifiers() -> int:
    """Run plugins/*/verify.sh; every plugin must ship one. Returns failures."""
    failures = 0
    print("plugin behaviour")
    plugins = sorted(p.parent.name for p in (ROOT / "plugins").glob("*/.claude-plugin"))
    if not shutil.which("bash"):
        print("  FAIL  bash is missing; no plugin verifier can run")
        return 1
    for name in plugins:
        verifier = ROOT / "plugins" / name / "verify.sh"
        if not verifier.is_file():
            failures += 1
            print(f"  FAIL  plugin {name} ships no verifier")
            continue
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
    return failures


def _tests() -> int:
    """Run the test suite. Returns failures."""
    print("tests")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", "tests"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    tail = (r.stdout or "").strip().splitlines()
    summary = tail[-1] if tail else (r.stderr or "").strip().splitlines()[-1:]
    if r.returncode == 0:
        print(f"  ok    {summary}")
        return 0
    print(f"  FAIL  {summary}")
    for line in tail:
        if line.startswith(("FAILED", "ERROR")):
            print(f"        {line}")
    return 1


def run(args: Sequence[str] = ()) -> int:
    failures, lines = fast()
    print("\n".join(lines))

    if "--fast" not in args:
        failures += _plugin_verifiers()
        failures += _tests()

    print()
    print("clean" if failures == 0 else f"{failures} problem(s)")
    return 1 if failures else 0
