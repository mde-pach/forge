"""
Where state lives, on every operating system.

Imported by every other module so there is exactly one answer. `os.uname()` does
not exist on Windows and `~/.local/state` is not a Windows convention, so both
were portability bugs waiting for the first person who is not on Linux.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path


def state_dir() -> Path:
    """Explicit override first, then the platform's own convention."""
    override = os.environ.get("FORGE_MONITOR_STATE")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / "forge-monitor"
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "forge-monitor"
    return (
        Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "forge-monitor"
    )


def hostname() -> str:
    """platform.node() works everywhere; os.uname() is POSIX-only."""
    return platform.node() or "unknown"


if __name__ == "__main__":
    # `python3 paths.py` prints the state directory, so the setup doc can tell
    # you yours without you having to know which platform convention applies.
    print(state_dir())
