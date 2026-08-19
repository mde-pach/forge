"""Create a project with its quality gates already wired."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence

from forge.registry import ROOT


def run(args: Sequence[str]) -> int:
    script = ROOT / "capabilities" / "scaffold" / "scaffold.sh"
    if not args:
        print("usage: forge scaffold <python|nextjs> <target-dir> [description]", file=sys.stderr)
        return 2
    return subprocess.run(["bash", str(script), *args], check=False).returncode
