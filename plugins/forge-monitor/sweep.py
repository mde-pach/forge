#!/usr/bin/env python3
"""
Mark records that stopped reporting.

No daemon watches for a session that died - a closed laptop lid fires no
SessionEnd, so a record would claim "working" forever. Instead the next session
to start sweeps: the system repairs itself whenever it is used, which is the
only moment the repair matters.

Run from the SessionStart hook, in the background.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths

# Two thresholds, and the distinction matters.
#
# STALE: we have not heard from this session in a while. That is a statement
# about OUR knowledge, not about the session - a session blocked on a permission
# prompt emits nothing precisely because it is waiting for you, and that is the
# single most important row on the dashboard. So a stale record keeps its state
# and its reason, and is only flagged. Hiding it would be the worst outcome:
# silently dropping the thing that has been waiting longest.
#
# FORGOTTEN: long enough that the record is noise. Removed outright.
DEFAULT_STALE_MINUTES = 45
DEFAULT_FORGET_HOURS = 72


def now() -> datetime:
    return datetime.now(UTC)


def parse(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def stale_minutes(state: Path) -> int:
    try:
        return int(
            json.loads((state / "config.json").read_text()).get(
                "stale_minutes", DEFAULT_STALE_MINUTES
            )
        )
    except (OSError, ValueError, TypeError):
        return DEFAULT_STALE_MINUTES


def forget_hours(state: Path) -> int:
    try:
        return int(
            json.loads((state / "config.json").read_text()).get(
                "forget_hours", DEFAULT_FORGET_HOURS
            )
        )
    except (OSError, ValueError, TypeError):
        return DEFAULT_FORGET_HOURS


def run(exclude: str | None = None) -> int:
    """Never raises. Returns the number of records touched."""
    state = paths.state_dir()
    limit = stale_minutes(state)
    forget = forget_hours(state)
    me = exclude
    swept = []

    for d in (state / "sessions",):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            if me and f.stem == me:
                continue
            try:
                rec = json.loads(f.read_text())
            except (OSError, ValueError):
                continue
            seen = parse(rec.get("last_seen"))
            age = (now() - seen).total_seconds() if seen else 1e9

            if rec.get("ended") and age > forget * 3600:
                f.unlink(missing_ok=True)
                swept.append(f.stem)
                continue
            if rec.get("ended") or age < limit * 60 or rec.get("stale"):
                continue

            # Deliberately does NOT touch state, attention_reason or ended. We
            # do not know that the session died; we know only that we stopped
            # hearing from it, and the dashboard says exactly that.
            rec["stale"] = True
            rec["stale_since"] = now().strftime("%Y-%m-%dT%H:%M:%SZ")
            rec["stale_reason"] = f"no events for over {limit} minutes"
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps(rec, indent=2))
            tmp.replace(f)
            swept.append(f.stem)

    # Marking a record locally is not enough - the store would keep claiming
    # those sessions are alive. Clearing published_at makes each one pending,
    # and the flush that follows this sweep sends them.
    for sid in swept:
        f = state / "sessions" / f"{sid}.json"
        try:
            rec = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        rec.pop("published_at", None)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec, indent=2))
        tmp.replace(f)
    return len(swept)


def main() -> int:
    run(sys.argv[1] if len(sys.argv) > 1 else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
