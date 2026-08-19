#!/usr/bin/env python3
"""
forge-monitor dashboard.

The store is the source of truth. This process holds no state of its own: it
pulls the store, reads every session record, and renders. That is what makes it
runnable from anywhere - your laptop, another machine, a box that is always on -
and why nothing breaks when it is not running at all. Sessions keep publishing;
this is only a window.

    python3 serve.py [--port 7373] [--state DIR]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).resolve().parent
PULL_EVERY = 20  # seconds; a request inside this window reads what we have


class Handler(SimpleHTTPRequestHandler):
    last_pull = 0.0

    def __init__(self, *a, state: Path, **kw):
        self.state = state
        super().__init__(*a, directory=str(HERE / "dashboard"), **kw)

    # ---- data -------------------------------------------------------------
    def _pull(self) -> None:
        store = self.state / "store"
        if not (store / ".git").is_dir():
            return
        if time.time() - Handler.last_pull < PULL_EVERY:
            return
        Handler.last_pull = time.time()
        for cmd in (["git", "fetch", "--quiet", "--depth", "1", "origin"],
                    ["git", "reset", "--quiet", "--hard", "FETCH_HEAD"]):
            try:
                subprocess.run(cmd, cwd=store, capture_output=True, timeout=30, check=False)
            except (subprocess.SubprocessError, OSError):
                return

    def _records(self) -> tuple[list[dict], str]:
        """Store first. Local records only when there is no store, so a machine
        that has not been configured yet still shows its own sessions."""
        store = self.state / "store" / "sessions"
        local = self.state / "sessions"
        src, where = (store, "store") if store.is_dir() else (local, "local")
        out = []
        for f in sorted(src.glob("*.json")):
            try:
                out.append(json.loads(f.read_text()))
            except (OSError, ValueError):
                continue
        return out, where

    def _snapshot(self) -> dict:
        self._pull()
        recs, where = self._records()
        key = lambda r: r.get("attention_since") or r.get("last_seen") or ""  # noqa: E731

        waiting = sorted((r for r in recs if r.get("needs_attention") and not r.get("ended")),
                         key=key)                       # oldest demand first
        running = sorted((r for r in recs if not r.get("needs_attention") and not r.get("ended")),
                         key=key, reverse=True)
        recent = sorted((r for r in recs if r.get("ended")), key=key, reverse=True)[:15]

        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": where,
            "counts": {"waiting": len(waiting), "running": len(running), "recent": len(recent)},
            "waiting": waiting, "running": running, "recent": recent,
        }

    # ---- http -------------------------------------------------------------
    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path in ("/snapshot.json", "/snapshot"):
            return self._json(self._snapshot())
        if path == "/healthz":
            return self._json({"ok": True})
        return super().do_GET()

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, *_a):
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("FORGE_MONITOR_PORT", 7373)))
    ap.add_argument("--state", default=os.environ.get("FORGE_MONITOR_STATE") or
                    str(Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) /
                        "forge-monitor"))
    args = ap.parse_args()
    state = Path(args.state)
    state.mkdir(parents=True, exist_ok=True)
    srv = HTTPServer(("127.0.0.1", args.port), partial(Handler, state=state))
    print(f"forge-monitor dashboard on http://127.0.0.1:{args.port}")
    print(f"  state: {state}")
    print("  reach it from your other devices: bash tailscale/expose.sh")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
