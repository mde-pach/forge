#!/usr/bin/env python3
"""
Is the monitor working, and if not, which step failed?

Run it after setup, or any time the dashboard looks wrong. It only reads: it
changes no files, publishes nothing, and needs no arguments.

    python3 doctor.py
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paths

# The keys the record folder reads out of a hook payload. If Claude Code names
# them differently, records come out empty and nothing reports an error - so
# this list is the single most important thing in the report.
EXPECTED = {
    "*": ["session_id", "cwd"],
    "SessionStart": ["session_start_reason"],
    "SessionEnd": ["session_end_reason"],
    "Notification": ["notification_type"],
    "Stop": ["last_assistant_message"],
}
KNOWN_NOTIFICATIONS = [
    "permission_prompt",
    "idle_prompt",
    "agent_needs_input",
    "agent_completed",
    "elicitation_dialog",
]


def h(title: str) -> None:
    print(f"\n{title}\n" + "-" * len(title))


def which(name: str) -> str:
    p = shutil.which(name)
    if not p:
        return "MISSING"
    for args in ([name, "--version"], [name, "version"]):
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
            if r.returncode == 0 and (r.stdout or r.stderr).strip():
                return (r.stdout or r.stderr).strip().splitlines()[0][:60]
        except (subprocess.SubprocessError, OSError):
            pass
    return "present"


def main() -> int:
    state = paths.state_dir()

    h("ENVIRONMENT")
    print(f"  platform     {platform.system()} {platform.release()} ({os.name})")
    print(f"  python       {platform.python_version()}")
    print(f"  hostname     {paths.hostname()}")
    for tool in ("claude", "gh", "git", "tailscale"):
        print(f"  {tool:<12} {which(tool)}")
    print(f"  state dir    {state}  ({'exists' if state.is_dir() else 'MISSING'})")

    h("CONFIG")
    cfg_path = state / "config.json"
    cfg = {}
    if not cfg_path.is_file():
        print(f"  {cfg_path} MISSING  -> nothing will ever be published")
    else:
        try:
            cfg = json.loads(cfg_path.read_text())
            store = cfg.get("store") or {}
            print(f"  store repo   {store.get('repo') or 'NOT SET -> nothing is published'}")
            print(f"  rate limit   {cfg.get('min_publish_seconds', 120)}s between routine pushes")
            print(f"  stale after  {cfg.get('stale_minutes', 45)} minutes")
        except ValueError as e:
            print(f"  config.json is not valid JSON: {e}")

    h("EVENTS RECEIVED")
    logs = sorted(state.glob("events-*.ndjson")) if state.is_dir() else []
    if not logs:
        print("  NOTHING. Either the plugin is not loaded, or hooks are not firing.")
        print("  Check with:  claude --debug   (look for forge-monitor)")
    payloads: dict[str, list[dict]] = {}
    for f in logs:
        ev = f.stem[len("events-") :]
        rows = []
        for line in f.read_text(errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
        payloads[ev] = rows
        print(f"  {ev:<16} {len(rows):>4} event(s)")

    h("FIELD DIFF   (what the code reads vs what actually arrived)")
    if not payloads:
        print("  no payloads yet - run a session first")
    for ev, rows in sorted(payloads.items()):
        if not rows:
            continue
        seen: set[str] = set()
        for r in rows:
            seen |= set(r.keys())
        want = EXPECTED["*"] + EXPECTED.get(ev, [])
        missing = [k for k in want if k not in seen]
        extra = sorted(
            seen
            - set(want)
            - {
                "hook_event_name",
                "transcript_path",
                "permission_mode",
                "prompt_id",
                "cwd",
                "session_id",
            }
        )
        status = "ok" if not missing else "MISSING " + ", ".join(missing)
        print(f"  {ev:<16} {status}")
        if extra:
            print(f"  {'':<16} also present: {', '.join(extra[:10])}")
        if ev == "Notification":
            types = sorted({r.get("notification_type") for r in rows if r.get("notification_type")})
            print(f"  {'':<16} notification types seen: {', '.join(types) or 'none'}")
            unknown = [t for t in types if t not in KNOWN_NOTIFICATIONS]
            if unknown:
                print(f"  {'':<16} NOT HANDLED BY THE CODE: {', '.join(unknown)}")

    h("RECORDS")
    sess = sorted((state / "sessions").glob("*.json")) if (state / "sessions").is_dir() else []
    if not sess:
        print("  none - no session has been folded into a record yet")
    for f in sess:
        try:
            r = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        pend = "" if (r.get("published_at") or "") >= (r.get("last_seen") or "") else "  PENDING"
        print(
            f"  {f.stem[:8]}  {r.get('state', '?'):<8} "
            f"{r.get('attention_reason') or '-':<20} {r.get('project') or '?':<16}"
            f"{' STALE' if r.get('stale') else ''}{pend}"
        )

    h("STORE")
    repo = (cfg.get("store") or {}).get("repo")
    if not repo:
        print("  no repo configured - skipping")
    else:
        try:
            import publish

            tok = publish.token(cfg)
            if not tok:
                print("  NO CREDENTIAL. Run: gh auth login")
            else:
                st, body, _ = publish.call(
                    "GET", f"https://api.github.com/repos/{repo}/contents/sessions", tok
                )
                meaning = {
                    200: "reachable",
                    404: "repo or sessions/ not there yet",
                    401: "credential rejected",
                    403: "forbidden or rate limited",
                    0: "no network",
                }.get(st, "unexpected")
                n = len(body) if isinstance(body, list) else 0
                print(
                    f"  GET sessions/  HTTP {st}  ({meaning})"
                    + (f", {n} file(s)" if st == 200 else "")
                )
        except Exception as e:  # noqa: BLE001 - a diagnostic must never crash
            print(f"  check failed: {e}")

    h("WHAT THE DASHBOARD WOULD SHOW")
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("srv", HERE / "serve.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        hh = m.Handler.__new__(m.Handler)
        hh.state = state
        snap = hh._snapshot()  # noqa: SLF001 - the diagnostic reports what the server would
        print(f"  source   {snap['source']}")
        print(f"  waiting  {snap['counts']['waiting']}")
        print(f"  running  {snap['counts']['running']}")
        print(f"  recent   {snap['counts']['recent']}")
    except Exception as e:  # noqa: BLE001
        print(f"  could not render: {e}")

    print("\nPaste all of the above.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
