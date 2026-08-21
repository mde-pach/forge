"""Where monitor state lives, per platform."""

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

    return platform.node() or "unknown"


if __name__ == "__main__":
    print(state_dir())
