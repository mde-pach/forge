#!/usr/bin/env python3
"""Fold one hook event into its session record; answer "publish" or "hold"."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths

ALWAYS_PUBLISH = {"SessionStart", "SessionEnd", "Notification", "StopFailure", "TeammateIdle"}

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

    return _cfg_seconds("min_publish_seconds", 120)


def heartbeat_interval() -> int:
    """Seconds after which an unchanged record publishes anyway."""
    return _cfg_seconds("heartbeat_publish_seconds", 900)


def content_hash(rec: dict) -> str:

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
            "last_event",
            "dirty_files",
        )
    }
    return hashlib.sha256(json.dumps(skim, sort_keys=True).encode()).hexdigest()[:16]


def dirty_count(cwd: str) -> int | None:

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
        else:
            # Unknown is not "whatever it was last time": a count that cannot
            # be measured now (repo gone, git gone, timeout) must not keep
            # asserting the old number on the dashboard.
            rec.pop("dirty_files", None)
    rec.setdefault("host", paths.hostname())
    rec.setdefault("first_seen", rec["last_seen"])

    ntype = p.get("notification_type")
    if event == "SessionStart":
        rec.update(
            state="working",
            attention_reason=None,
            ended=False,
            start_reason=p.get("source"),
        )
    elif event == "SessionEnd":
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
        if p.get("stop_hook_active"):
            rec.update(state="working", attention_reason=None, attention_since=None)
        else:
            rec.update(state="idle", attention_reason=None, attention_since=None)
            msg = p.get("last_assistant_message")
            if isinstance(msg, str) and msg.strip():
                rec["last_message"] = msg.strip()[:280]
    elif event in ("SubagentStart", "SubagentStop", "TaskCreated", "TaskCompleted", "PreCompact"):
        rec.update(state="working", attention_reason=None, attention_since=None)

    rec["needs_attention"] = bool(rec.get("attention_reason")) and not rec.get("ended")


def handle(event: str, payload: dict) -> str:

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
    tmp.replace(f)

    # Changed: publish now if urgent, else at the floor. Unchanged: heartbeat only.
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

    event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = {}
    print(handle(event, payload if isinstance(payload, dict) else {}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
