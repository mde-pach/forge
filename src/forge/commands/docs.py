"""Build the documentation site, verify the generated pages are current, or preview it."""

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
VITEPRESS = ROOT / "node_modules" / ".bin" / "vitepress"  # by path: npx may fetch another version


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
    if not VITEPRESS.is_file():
        print("docs: node_modules is missing - run `npm ci` first", file=sys.stderr)
        return 2
    return subprocess.run([str(VITEPRESS), subcommand, "docs"], cwd=ROOT, check=False).returncode


def _check() -> int:
    """Regenerate into scratch and compare with the previous build, if there was one."""
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
