"""Report what is working, and which step failed if something is not."""

from __future__ import annotations

import runpy
import sys
from collections.abc import Sequence

from forge.registry import ROOT


def run(args: Sequence[str]) -> int:
    sys.argv = ["doctor", *args]
    runpy.run_path(str(ROOT / "plugins" / "forge-monitor" / "doctor.py"), run_name="__main__")
    return 0
