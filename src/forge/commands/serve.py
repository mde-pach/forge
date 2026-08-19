"""Serve the session view. Thin: the implementation lives with the plugin."""

from __future__ import annotations

import runpy
import sys
from collections.abc import Sequence

from forge.registry import ROOT


def run(args: Sequence[str]) -> int:
    sys.argv = ["serve", *args]
    runpy.run_path(str(ROOT / "plugins" / "forge-monitor" / "serve.py"), run_name="__main__")
    return 0
