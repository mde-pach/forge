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

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths

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
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cfg_seconds(key: str, default: int) -> int:
    try:
        cfg = json.loads((paths.state_dir() / "config.json").read_text())
        return int(cfg.get(key, default))
    except (OSError, ValueError, TypeError):
        return default


def min_publish_interval() -> int:
    """Seconds between pushes for non-urgent changes. Attention never waits."""
    return _cfg_seconds("min_publish_seconds", 120)


def heartbeat_interval() -> int:
    """Seconds after which an UNCHANGED record publishes anyway, so the store's
    last_seen stays honest enough for the dashboard's staleness maths."""
    return _cfg_seconds("heartbeat_publish_seconds", 900)


def content_hash(rec: dict) -> str:
    """What a human would notice changing, hashed.

    Excludes the fields that change on every event or every publish attempt
    (last_seen and the bookkeeping) - left in, every event is a "change" and
    coalescing is a rate limit rather than a difference test. That is not
    hypothetical: the first monitored session put ten commits in the store,
    seven of them saying "idle" and differing only in last_seen, one every two
    minutes for as long as the session ran.
    """
    skim = {
        k: v
        for k, v in rec.items()
        if k
        not in (
            "last_seen",
            "published_at",
            "publish_attempted_at",
            "publish_attempted_hash",
            "store_sha",
            # Deliberately churn, not change: the count moves with nearly every
            # tool call during honest work, and hashing it would bring back the
            # metronome this hash exists to silence. It rides along on whatever
            # publish happens next - in particular on SessionEnd, which is the
            # moment "ended with N uncommitted files" is the headline.
            "dirty_files",
        )
    }
    return hashlib.sha256(json.dumps(skim, sort_keys=True).encode()).hexdigest()[:16]


def dirty_count(cwd: str) -> int | None:
    """How many files `git status` would show in the session's working tree.

    The first monitored session ended reporting its work "fully reviewed and
    verified" while every line of it existed uncommitted, on one machine - the
    exact loss mode the store exists to prevent, invisible on the dashboard
    built to prevent it. The record now carries the count; None means cwd is
    not a git repo (or git is missing), which is not the monitor's business.
    """
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    if r.returncode != 0:
        return None
    return sum(1 for line in r.stdout.splitlines() if line.strip())


def since(iso: str | None) -> float:
    if not iso:
        return 1e9
    try:
        t = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return 1e9
    return (datetime.now(UTC) - t).total_seconds()


def fold(rec: dict, event: str, p: dict) -> None:
    """Update the record in place. Whether anything human-visible changed is
    content_hash()'s question, asked by handle() - this used to return a
    state-flip flag, which missed message changes and double-counted flips."""
    rec["session_id"] = p.get("session_id") or rec.get("session_id")
    rec["last_seen"] = now()
    rec["last_event"] = event
    for k in ("cwd", "permission_mode"):
        if p.get(k):
            rec[k] = p[k]
    if p.get("cwd"):
        rec["project"] = Path(p["cwd"]).name
        d = dirty_count(p["cwd"])
        if d is not None:
            rec["dirty_files"] = d
    rec.setdefault("host", paths.hostname())
    rec.setdefault("first_seen", rec["last_seen"])

    ntype = p.get("notification_type")
    if event == "SessionStart":
        # The payload calls it `source` (startup/resume/clear/compact). Still
        # written to documentation, not to a captured payload: SessionStart has
        # never been observed to fire here - no events-SessionStart.ndjson
        # exists - which is an open question of its own. Until one is captured,
        # the fixture replay (verify.sh 11) skips this event, and says so.
        rec.update(
            state="working",
            attention_reason=None,
            ended=False,
            start_reason=p.get("source"),
        )
    elif event == "SessionEnd":
        # The payload calls it `reason`, not `session_end_reason`. The first
        # record ever published shipped end_reason: null because this line was
        # written to a guessed name and nothing compared it to a real payload.
        # The comparison is now a check: verify.sh 11 replays a captured
        # payload through fold() and fails when this comes back null.
        rec.update(state="ended", attention_reason=None, ended=True, end_reason=p.get("reason"))
    elif event == "Notification" and ntype in ATTENTION:
        rec.update(
            state="blocked",
            attention_reason=ATTENTION[ntype],
            attention_since=rec.get("attention_since") or now(),
        )
    elif event == "Notification" and ntype in FINISHED:
        rec.update(
            state="idle",
            attention_reason="finished",
            attention_since=rec.get("attention_since") or now(),
        )
    elif event == "TeammateIdle":
        rec.update(
            state="idle",
            attention_reason="idle",
            attention_since=rec.get("attention_since") or now(),
        )
    elif event == "StopFailure":
        rec.update(state="failed", attention_reason="turn failed", attention_since=now())
    elif event == "Stop":
        # stop_hook_active means a Stop hook forced the turn to CONTINUE - a
        # gate arguing with the session. That is work, not rest: 45 of the
        # first real session's 47 Stop events were these, and each one was
        # recorded as "idle" (with mid-argument narration as last_message)
        # while the session spun against its guard at full tilt.
        if p.get("stop_hook_active"):
            rec.update(state="working", attention_reason=None, attention_since=None)
        else:
            # A turn actually ended. Not a demand by itself - it does clear one.
            rec.update(state="idle", attention_reason=None, attention_since=None)
            msg = p.get("last_assistant_message")
            if isinstance(msg, str) and msg.strip():
                rec["last_message"] = msg.strip()[:280]
    elif event in ("SubagentStart", "SubagentStop", "TaskCreated", "TaskCompleted", "PreCompact"):
        rec.update(state="working", attention_reason=None, attention_since=None)

    rec["needs_attention"] = bool(rec.get("attention_reason")) and not rec.get("ended")


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

    fold(rec, event, payload)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=2))
    tmp.replace(f)  # atomic: a reader never sees a half-written record

    # A publish needs a DIFFERENCE, not just an event. The old rule published
    # every ALWAYS_PUBLISH event unconditionally and every state flip at a
    # 120-second floor, which turned one guard-blocked session into a commit
    # every two minutes saying nothing new. Now: a changed record publishes -
    # immediately when it is urgent (lifecycle events, a session demanding
    # attention), at the floor otherwise - and an UNCHANGED record publishes
    # only as a slow heartbeat, so the store's last_seen cannot silently drift
    # a whole workday. Still gated on the last ATTEMPT, not the last success:
    # gating on success would spin on every event whenever the sink is broken,
    # the moment you least want extra work happening in a hook.
    h = content_hash(rec)
    hash_changed = h != rec.get("publish_attempted_hash")
    urgent = event in ALWAYS_PUBLISH or rec.get("needs_attention")
    idle_for = since(rec.get("publish_attempted_at"))
    go = bool(
        (hash_changed and (urgent or idle_for >= min_publish_interval()))
        or idle_for >= heartbeat_interval()
    )
    if go:
        rec["publish_attempted_at"] = now()
        rec["publish_attempted_hash"] = h
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
