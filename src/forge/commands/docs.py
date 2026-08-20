"""
The documentation site: build it, verify it is current, or preview it.

There is one caller of `assemble.mjs` and this is it. There used to be three -
`docs:dev` and `docs:build` in package.json, plus this command added last -
which is the same "second mechanism for one job" the registry exists to stop,
gotten in through a door the registry does not watch. CI used the npm one and
nothing used this one.

`--check` regenerates into a scratch copy and fails if anything differs from
what is committed. That is the whole mechanism for keeping generated prose
honest: a human never maintains it, so it cannot drift, and a stale commit is a
red build rather than a page that quietly lies.
"""

from __future__ import annotations

import filecmp
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from forge.registry import ROOT

GENERATED = ROOT / "docs" / "generated"
ASSEMBLE = ROOT / "docs" / ".vitepress" / "assemble.mjs"
VITEPRESS = ROOT / "node_modules" / ".bin" / "vitepress"


def _assemble() -> int:
    if not shutil.which("node"):
        print("docs: node is not installed", file=sys.stderr)
        return 2
    r = subprocess.run(
        ["node", str(ASSEMBLE)], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
    return r.returncode


def _vitepress(subcommand: str) -> int:
    """The local binary by path, not `npx`. `npx` will happily fetch a different
    version from the network when node_modules is incomplete, which turns a
    missing install into a silently different build."""
    if not VITEPRESS.is_file():
        print("docs: node_modules is missing - run `npm ci` first", file=sys.stderr)
        return 2
    return subprocess.run([str(VITEPRESS), subcommand, "docs"], cwd=ROOT, check=False).returncode


def _check() -> int:
    # docs/generated is a build artifact and is gitignored, so "stale" only
    # means something when there is a previous build to compare against. On a
    # clean checkout there is nothing to drift from, and reporting drift there
    # would be a check that fails for the wrong reason - the exact habit this
    # command exists to break.
    existed = GENERATED.is_dir() and any(GENERATED.iterdir())
    before = Path(tempfile.mkdtemp()) / "generated"
    if existed:
        shutil.copytree(GENERATED, before)
    else:
        before.mkdir(parents=True)

    rc = _assemble()
    if rc != 0:
        return rc
    if not existed:
        print("generated documentation built from a clean checkout")
        return 0

    cmp_result = filecmp.dircmp(str(before), str(GENERATED))
    drifted = sorted(cmp_result.diff_files + cmp_result.left_only + cmp_result.right_only)
    if drifted:
        for f in drifted:
            print(f"  STALE  docs/generated/{f}")
        print("generated documentation is out of date; run `forge docs`", file=sys.stderr)
        return 1
    print("generated documentation is current")
    return 0


def run(args: Sequence[str] = ()) -> int:
    if "--check" in args:
        return _check()

    rc = _assemble()
    if rc != 0:
        return rc

    if "--dev" in args:
        print("docs: live preview; ctrl-c to stop")
        return _vitepress("dev")

    rc = _vitepress("build")
    if rc == 0:
        print("docs: built into docs/.vitepress/dist")
    return rc
