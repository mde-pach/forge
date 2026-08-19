#!/usr/bin/env python3
"""
The hook body. Everything the monitor does inside a session happens here.

Written in Python, not shell, for one reason: it has to work on Linux, macOS and
Windows. The shell version used `timeout`, which macOS does not ship, and
assumed a bash newer than the 3.2 macOS has carried since 2007. Python is
already required by the rest of the plugin, so this removes a dependency rather
than adding one.

THE CONTRACT, in order of importance:

  1. It writes NOTHING to stdout, ever. Claude Code shows a hook's stdout to the
     model on exactly three events (SessionStart, UserPromptSubmit,
     UserPromptExpansion); printing nothing means no session can observe this
     layer on any event.
  2. It always exits 0. Exit 2 is a blocking error on several events. A gate
     must fail closed; a monitor must fail open, because one that can stop a
     turn eventually will, at the worst moment.
  3. It bounds itself. A watchdog exits the process rather than letting a hung
     network call linger.
"""

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
    """Hard ceiling. os._exit skips interpreter shutdown on purpose: this must
    not raise, print, or run an atexit handler that might."""
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
    """The audit trail, and the fixtures we will finally test against."""
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

    # A session starting is the moment to repair what nobody was watching: a
    # machine that shut down mid-session fires no SessionEnd, so that record
    # would claim to be running forever.
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
