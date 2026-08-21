#!/usr/bin/env python3
"""Mark records that stopped reporting; run from the SessionStart hook.

A record that has not been heard from for STALE minutes is flagged but keeps
its state (a session blocked on a permission prompt emits nothing). An ended
record older than FORGET hours is removed.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths

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

            rec["stale"] = True
            rec["stale_since"] = now().strftime("%Y-%m-%dT%H:%M:%SZ")
            rec["stale_reason"] = f"no events for over {limit} minutes"
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps(rec, indent=2))
            tmp.replace(f)
            swept.append(f.stem)

    # Clearing published_at makes each swept record pending for the flush that follows.
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
