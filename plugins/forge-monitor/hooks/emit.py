#!/usr/bin/env python3
"""The monitor's hook body. Contract: writes nothing to stdout, always exits 0, bounded by a watchdog."""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

WATCHDOG_SECONDS = 90


def watchdog() -> None:
    """Hard ceiling; os._exit so that nothing can print or raise on the way out."""
    os._exit(0)


def read_payload() -> dict:
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def log_raw(state: Path, event: str, payload: dict) -> None:
    """Append the raw payload to events-<Event>.ndjson."""
    try:
        state.mkdir(parents=True, exist_ok=True)
        f = state / f"events-{event}.ndjson"
        if f.exists() and f.stat().st_size > 5_000_000:
            f.replace(f.with_suffix(".ndjson.1"))
        with f.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except OSError:
        pass


def main() -> int:
    t = threading.Timer(WATCHDOG_SECONDS, watchdog)
    t.daemon = True
    t.start()

    event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    payload = read_payload()

    import paths

    state = paths.state_dir()
    log_raw(state, event, payload)

    sid = payload.get("session_id")

    import record

    decision = record.handle(event, payload)

    if event == "SessionStart":
        import sweep

        sweep.run(exclude=sid)

    import publish

    if decision == "publish" and sid:
        publish.one(sid)
    if decision == "publish" or event == "SessionStart":
        publish.flush()

    return 0


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass  # a monitor never takes the session with it
    sys.stdout.flush()
    os._exit(0)
