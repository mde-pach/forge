#!/usr/bin/env python3
"""
forge-monitor dashboard server.

Binds loopback only. Reaching it from a phone is Tailscale's job (see
tailscale/expose.sh), so this process never listens on a routable address and
there is nothing to firewall, no TLS to renew and no port to forward.

    python3 serve.py [--port 7373] [--state DIR]
"""

from __future__ import annotations

import argparse
import json
import os
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, state: Path, **kw):
        self.state = state
        super().__init__(*a, directory=str(HERE / "dashboard"), **kw)

    def do_GET(self):  # noqa: N802
        if self.path.split("?")[0] in ("/snapshot.json", "/snapshot"):
            return self._snapshot()
        if self.path.split("?")[0] == "/healthz":
            return self._json({"ok": True})
        return super().do_GET()

    def _snapshot(self):
        try:
            body = (self.state / "snapshot.json").read_bytes()
        except OSError:
            # The collector has not run yet. An empty but well-formed snapshot
            # renders as "nothing needs you", which is true, rather than as an
            # error the user has to interpret.
            body = json.dumps({
                "generated_at": None,
                "counts": {"waiting": 0, "active": 0, "recent": 0},
                "waiting": [], "active": [], "recent": [],
            }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, *_a):  # quiet: this runs as a daemon
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("FORGE_MONITOR_PORT", 7373)))
    ap.add_argument("--state", default=os.environ.get("FORGE_MONITOR_STATE") or
                    str(Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "forge-monitor"))
    args = ap.parse_args()
    state = Path(args.state)
    state.mkdir(parents=True, exist_ok=True)
    srv = HTTPServer(("127.0.0.1", args.port), partial(Handler, state=state))
    print(f"forge-monitor dashboard on http://127.0.0.1:{args.port}  (state: {state})")
    print("expose it to your other devices with: bash tailscale/expose.sh")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
