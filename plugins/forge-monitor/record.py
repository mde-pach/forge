#!/usr/bin/env python3
"""
Fold one hook event into that session's record.

A session is the unit. The machine it runs on is a field on the record, like
the working directory - two sessions on two machines are just two sessions.
That is why there is one file per session and no merge step: no two writers
ever touch the same file, so pushes never conflict on content.

Reads the raw hook payload on stdin. Prints one word on stdout for the caller:
  publish   this change is worth pushing now
  hold      recorded locally, not worth a push yet
Nothing here ever reaches the session: the hook that calls it discards output.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

# Events that change what a human would want to know, so they justify a push.
# Everything else is recorded and rides along with the next one.
ALWAYS_PUBLISH = {"SessionStart", "SessionEnd", "Notification", "StopFailure", "TeammateIdle"}

# Notification types that mean the session is blocked on the human.
ATTENTION = {
    "permission_prompt": "permission request",
    "idle_prompt": "idle, waiting for you",
    "agent_needs_input": "needs input",
    "elicitation_dialog": "dialog open",
    "elicitation_url_dialog": "dialog open (url)",
}
FINISHED = {"agent_completed": "finished"}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")



def min_publish_interval() -> int:
    """Seconds between pushes for non-urgent events. Attention never waits."""
    try:
        cfg = json.loads((paths.state_dir() / "config.json").read_text())
        return int(cfg.get("min_publish_seconds", 120))
    except (OSError, ValueError, TypeError):
        return 120


def since(iso: str | None) -> float:
    if not iso:
        return 1e9
    try:
        t = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return 1e9
    return (datetime.now(timezone.utc) - t).total_seconds()


def fold(rec: dict, event: str, p: dict) -> bool:
    """Update the record in place. Returns True if a human-visible thing changed."""
    before = (rec.get("state"), rec.get("attention_reason"))

    rec["session_id"] = p.get("session_id") or rec.get("session_id")
    rec["last_seen"] = now()
    rec["last_event"] = event
    for k in ("cwd", "permission_mode"):
        if p.get(k):
            rec[k] = p[k]
    if p.get("cwd"):
        rec["project"] = Path(p["cwd"]).name
    rec.setdefault("host", paths.hostname())
    rec.setdefault("first_seen", rec["last_seen"])

    ntype = p.get("notification_type")
    if event == "SessionStart":
        rec.update(state="working", attention_reason=None, ended=False,
                   start_reason=p.get("session_start_reason"))
    elif event == "SessionEnd":
        rec.update(state="ended", attention_reason=None, ended=True,
                   end_reason=p.get("session_end_reason"))
    elif event == "Notification" and ntype in ATTENTION:
        rec.update(state="blocked", attention_reason=ATTENTION[ntype],
                   attention_since=rec.get("attention_since") or now())
    elif event == "Notification" and ntype in FINISHED:
        rec.update(state="idle", attention_reason="finished",
                   attention_since=rec.get("attention_since") or now())
    elif event == "TeammateIdle":
        rec.update(state="idle", attention_reason="idle",
                   attention_since=rec.get("attention_since") or now())
    elif event == "StopFailure":
        rec.update(state="failed", attention_reason="turn failed",
                   attention_since=now())
    elif event == "Stop":
        # A turn ended. Not a demand by itself - the gate may have blocked it
        # and the session may carry on. It does clear a previous demand.
        rec.update(state="idle", attention_reason=None, attention_since=None)
        msg = p.get("last_assistant_message")
        if isinstance(msg, str) and msg.strip():
            rec["last_message"] = msg.strip()[:280]
    elif event in ("SubagentStart", "SubagentStop", "TaskCreated", "TaskCompleted", "PreCompact"):
        rec.update(state="working", attention_reason=None, attention_since=None)

    rec["needs_attention"] = bool(rec.get("attention_reason")) and not rec.get("ended")
    return before != (rec.get("state"), rec.get("attention_reason"))


def handle(event: str, payload: dict) -> str:
    """Returns "publish" or "hold". Never raises."""
    sid = payload.get("session_id")
    if not sid:
        return "hold"

    d = paths.state_dir() / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{sid}.json"
    try:
        rec = json.loads(f.read_text())
    except (OSError, ValueError):
        rec = {}

    changed = fold(rec, event, payload)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=2))
    tmp.replace(f)  # atomic: a reader never sees a half-written record

    # Coalescing is about rate, so it is gated on the last ATTEMPT, not the last
    # success. Gating on success would spin on every event whenever the sink is
    # broken - the moment you least want extra work happening in a hook.
    urgent = event in ALWAYS_PUBLISH or rec.get("needs_attention")
    stale = since(rec.get("publish_attempted_at")) >= min_publish_interval()
    go = bool(urgent or (changed and stale))
    if go:
        rec["publish_attempted_at"] = now()
        tmp.write_text(json.dumps(rec, indent=2))
        tmp.replace(f)
    return "publish" if go else "hold"


def main() -> int:
    """Runnable alone, for debugging:  cat payload.json | python3 record.py Stop"""
    event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = {}
    print(handle(event, payload if isinstance(payload, dict) else {}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
