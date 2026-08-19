"""Reach the session view from your other devices, over Tailscale."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence

from forge.registry import ROOT


def run(args: Sequence[str]) -> int:
    script = ROOT / "plugins" / "forge-monitor" / "tailscale" / "expose.sh"
    return subprocess.run(["sh", str(script), *args], check=False).returncode
