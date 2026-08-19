#!/usr/bin/env python3
"""
forge-monitor collector — folds session telemetry into a publishable state.

This process is deliberately NOT part of any Claude Code session. It runs as a
user daemon, reads what the hook emitter appended and what `claude agents`
reports, and publishes through a sink. Nothing here is reachable from a session:
no skill describes it, no tool invokes it, no MCP server exposes it, and the
credential it publishes with lives in this process's config, not in any
session's environment.

That separation is the design, not an implementation detail. The sink is an
interface for the same reason: replacing GitHub with anything else must not
touch the hooks, and must not be observable from a session either.

Run:  python3 collector.py --once      (one pass, for testing and cron)
      python3 collector.py --watch     (loop)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_DIR = Path(
    os.environ.get("FORGE_MONITOR_STATE")
    or Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "forge-monitor"
)
EVENTS = STATE_DIR / "events.ndjson"
OFFSET = STATE_DIR / ".offset"
SESSIONS = STATE_DIR / "sessions.json"
SNAPSHOT = STATE_DIR / "snapshot.json"
STATUS_MD = STATE_DIR / "STATUS.md"
CONFIG = STATE_DIR / "config.json"

# Events that mean "this session is now waiting on the human", mapped to the
# reason to show. Sourced from the documented Notification types plus the
# session-level events; anything unlisted is treated as activity, not a demand.
ATTENTION = {
    "permission_prompt": "permission request",
    "idle_prompt": "idle, waiting for you",
    "agent_needs_input": "needs input",
    "elicitation_dialog": "dialog open",
    "elicitation_url_dialog": "dialog open (url)",
}
DONE = {"agent_completed": "completed"}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(p: Path, default: Any) -> Any:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def read_new_events() -> list[dict]:
    """Read events appended since the last pass. Survives log rotation."""
    if not EVENTS.exists():
        return []
    off = load_json(OFFSET, {})
    try:
        size = EVENTS.stat().st_size
    except OSError:
        return []
    start = off.get("pos", 0)
    if start > size:  # rotated or truncated
        start = 0
    out: list[dict] = []
    try:
        with EVENTS.open("r", errors="replace") as fh:
            fh.seek(start)
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue  # a partial line mid-append; it will be re-read next pass
            pos = fh.tell()
    except OSError:
        return []
    # Only advance past whole lines.
    OFFSET.write_text(json.dumps({"pos": pos}))
    return out


def poll_agents() -> list[dict]:
    """`claude agents --json` is the runtime's own view. Local machine only."""
    if not shutil.which("claude"):
        return []
    try:
        r = subprocess.run(
            ["claude", "agents", "--json", "--all"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return []
        data = json.loads(r.stdout)
        return data if isinstance(data, list) else data.get("agents", [])
    except (subprocess.SubprocessError, OSError, ValueError):
        return []


def short(path: str | None) -> str:
    if not path:
        return "?"
    home = str(Path.home())
    p = path[len(home) + 1:] if path.startswith(home + "/") else path
    return p.split("/")[-1] or p


def fold(sessions: dict, events: list[dict], agents: list[dict]) -> dict:
    for e in events:
        sid = e.get("session_id")
        if not sid:
            continue
        s = sessions.setdefault(sid, {"session_id": sid, "first_seen": e.get("at")})
        s["last_event"] = e.get("forge_event")
        s["last_seen"] = e.get("at") or now()
        for k in ("cwd", "host", "permission_mode"):
            if e.get(k):
                s[k] = e[k]
        if e.get("cwd"):
            s["project"] = short(e["cwd"])

        ev, ntype = e.get("forge_event"), e.get("notification_type")
        if ev == "SessionStart":
            s.update(state="working", needs_attention=False, attention_reason=None,
                     ended=False, start_reason=e.get("session_start_reason"))
        elif ev == "SessionEnd":
            s.update(state="ended", needs_attention=False, attention_reason=None,
                     ended=True, end_reason=e.get("session_end_reason"))
        elif ev == "Notification" and ntype in ATTENTION:
            s.update(state="blocked", needs_attention=True, attention_reason=ATTENTION[ntype],
                     attention_since=e.get("at") or now())
        elif ev == "Notification" and ntype in DONE:
            s.update(state="idle", needs_attention=True, attention_reason="finished",
                     attention_since=e.get("at") or now())
        elif ev in ("TeammateIdle",):
            s.update(state="idle", needs_attention=True, attention_reason="idle",
                     attention_since=e.get("at") or now())
        elif ev in ("Stop", "StopFailure"):
            # The turn ended. Not an attention event by itself: the gate may
            # have blocked it and the session may keep going.
            s["state"] = "idle" if ev == "Stop" else "failed"
            if ev == "StopFailure":
                s.update(needs_attention=True, attention_reason="turn failed")
            last = e.get("last_assistant_message")
            if isinstance(last, str) and last.strip():
                s["last_message"] = last.strip()[:280]
        elif ev in ("UserPromptSubmit", "PreToolUse", "PostToolUse", "SubagentStart"):
            s.update(state="working", needs_attention=False, attention_reason=None)

    # The runtime's own view wins on liveness: it knows about sessions that
    # died without emitting SessionEnd, which a crash always does.
    live = set()
    for a in agents:
        sid = a.get("sessionId") or a.get("session_id")
        if not sid:
            continue
        live.add(sid)
        s = sessions.setdefault(sid, {"session_id": sid, "first_seen": now()})
        s["last_seen"] = now()
        s.setdefault("host", os.uname().nodename)
        for k in ("name", "kind", "pid", "cwd"):
            if a.get(k) is not None:
                s[k] = a[k]
        if a.get("cwd"):
            s["project"] = short(a["cwd"])
        # An interactive session that has never registered a job record comes
        # back with no `state` at all - it is simply alive. Absent is not
        # unknown here: being listed IS the state.
        s["state"] = a.get("state") or s.get("state") or "working"
        if a.get("waitingFor"):
            s.update(needs_attention=True, attention_reason=a["waitingFor"])
        elif a.get("state") == "working":
            s.update(needs_attention=False, attention_reason=None)
        s["ended"] = a.get("state") in ("done", "failed", "stopped")

    if agents:  # only trust absence when the poll actually worked
        for sid, s in sessions.items():
            if sid not in live and not s.get("ended") and s.get("host") == os.uname().nodename:
                s["state"] = "gone"
                s["ended"] = True
    return sessions


def prune(sessions: dict, keep_hours: int = 72) -> dict:
    cut = time.time() - keep_hours * 3600
    out = {}
    for sid, s in sessions.items():
        try:
            ts = datetime.strptime(s.get("last_seen", ""), "%Y-%m-%dT%H:%M:%SZ")
            ts = ts.replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            ts = time.time()
        if not s.get("ended") or ts > cut:
            out[sid] = s
    return out


def render(sessions: dict) -> tuple[dict, str]:
    rows = sorted(sessions.values(), key=lambda s: s.get("last_seen", ""), reverse=True)
    waiting = [s for s in rows if s.get("needs_attention") and not s.get("ended")]
    active = [s for s in rows if not s.get("needs_attention") and not s.get("ended")]
    recent = [s for s in rows if s.get("ended")][:10]

    snap = {
        "generated_at": now(),
        "counts": {"waiting": len(waiting), "active": len(active), "recent": len(recent)},
        "waiting": waiting, "active": active, "recent": recent,
    }

    def line(s: dict) -> str:
        return (f"| `{s.get('project', '?')}` | {s.get('state', '?')} | "
                f"{s.get('attention_reason') or '—'} | {s.get('host', '?')} | "
                f"{s.get('last_seen', '?')} | `{str(s.get('session_id', ''))[:8]}` |")

    md = [f"# Sessions\n", f"_{now()} · {len(waiting)} waiting · {len(active)} active_\n"]
    if waiting:
        md += ["## Waiting on you\n",
               "| project | state | why | machine | since | id |",
               "|---|---|---|---|---|---|"]
        md += [line(s) for s in waiting]
        md.append("")
    else:
        md.append("## Waiting on you\n\nNothing.\n")
    if active:
        md += ["## Running\n",
               "| project | state | why | machine | last seen | id |",
               "|---|---|---|---|---|---|"]
        md += [line(s) for s in active]
        md.append("")
    if recent:
        md += ["## Recently finished\n",
               "| project | state | why | machine | ended | id |",
               "|---|---|---|---|---|---|"]
        md += [line(s) for s in recent]
        md.append("")
    return snap, "\n".join(md) + "\n"


def publish(cfg: dict, snap: dict, md: str) -> str:
    """Sinks are processes, not imports: a sink can be replaced, or removed,
    without this file changing and without any session noticing."""
    sink = cfg.get("sink", {})
    kind = sink.get("type", "none")
    if kind == "none":
        return "none (local only)"
    script = Path(__file__).parent / "sinks" / f"{kind}.sh"
    if not script.exists():
        return f"unknown sink '{kind}'"
    try:
        r = subprocess.run(
            ["bash", str(script)],
            input=json.dumps({"config": sink, "snapshot": snap, "status_md": md}),
            capture_output=True, text=True, timeout=120, check=False,
        )
        return (r.stdout or r.stderr or "").strip()[:400] or f"exit {r.returncode}"
    except (subprocess.SubprocessError, OSError) as exc:
        return f"sink error: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=int, default=30)
    args = ap.parse_args()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_json(CONFIG, {})

    def pass_once() -> None:
        sessions = load_json(SESSIONS, {})
        sessions = fold(sessions, read_new_events(), poll_agents())
        sessions = prune(sessions)
        SESSIONS.write_text(json.dumps(sessions, indent=2))
        snap, md = render(sessions)
        SNAPSHOT.write_text(json.dumps(snap, indent=2))
        STATUS_MD.write_text(md)
        result = publish(cfg, snap, md)
        print(f"{now()} waiting={snap['counts']['waiting']} "
              f"active={snap['counts']['active']} sink={result}", file=sys.stderr)

    if args.watch:
        while True:
            try:
                pass_once()
            except Exception as exc:  # a monitor that dies is worse than one that stumbles
                print(f"{now()} collector error: {exc}", file=sys.stderr)
            time.sleep(args.interval)
    else:
        pass_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
