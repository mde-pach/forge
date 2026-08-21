#!/usr/bin/env python3
"""forge-monitor dashboard: serves the store, read live over the GitHub API with conditional requests.

Holds no durable state. Run only by `forge start`, which also uses load_config
and find_token from here.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import ClassVar

HERE = Path(__file__).resolve().parent


def load_config(state: Path) -> dict:
    try:
        return json.loads((state / "config.json").read_text())
    except (OSError, ValueError):
        return {}


def api(url: str, tok: str, etag: str | None = None):
    """(status, json or None, etag); status 0 means no response."""
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "forge-monitor")
    if etag:
        req.add_header("If-None-Match", etag)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None), r.headers.get("ETag")
    except urllib.error.HTTPError as e:
        return e.code, None, e.headers.get("ETag")
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return 0, None, None


def find_token(cfg: dict) -> str | None:

    for var in ("FORGE_MONITOR_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        r = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=10, check=False
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    tf = (cfg.get("store") or {}).get("token_file")
    if tf:
        try:
            return Path(tf).expanduser().read_text().strip() or None
        except OSError:
            pass
    return None


class Handler(SimpleHTTPRequestHandler):
    # Platform mimetypes differ; a wrong manifest type breaks the PWA install.
    extensions_map: ClassVar[dict[str, str]] = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".webmanifest": "application/manifest+json",
        ".js": "text/javascript",
    }

    def __init__(self, *a, state: Path, **kw):
        self.state = state
        super().__init__(*a, directory=str(HERE / "dashboard"), **kw)

    # ---- data -------------------------------------------------------------
    _etag: str | None = None
    _cache: ClassVar[dict[str, dict]] = {}  # path -> {sha, record}
    _last_good: ClassVar[list[dict]] = []
    _online: bool | None = None

    def _cfg(self) -> dict:
        return load_config(self.state)

    def _token(self, cfg: dict) -> str | None:
        return find_token(cfg)

    def _api(self, url: str, tok: str, etag: str | None = None):
        return api(url, tok, etag)

    def _from_store(self) -> list[dict] | None:
        cfg = self._cfg()
        repo = (cfg.get("store") or {}).get("repo")
        branch = (cfg.get("store") or {}).get("branch", "main")
        if not repo:
            return None
        tok = self._token(cfg)
        if not tok:
            return None

        url = f"https://api.github.com/repos/{repo}/contents/sessions?ref={branch}"
        status, listing, etag = self._api(url, tok, Handler._etag)

        if status == 304:
            Handler._online = True
            return Handler._last_good  # nothing changed; free
        if status == 404:
            # 404 means either "no sessions yet" or "no such repo/branch"; only the
            # first may render as an empty dashboard, so probe the exact branch.
            probe_status, _, _ = self._api(
                f"https://api.github.com/repos/{repo}/branches/{branch}", tok
            )
            if probe_status == 200:
                Handler._online = True
                Handler._last_good = []
                Handler._etag = None  # the retained listing etag described a different world
                return []  # store exists, no sessions yet
            Handler._online = False
            return Handler._last_good or None  # stale beats blank
        if status != 200 or not isinstance(listing, list):
            Handler._online = False
            return Handler._last_good or None  # stale beats blank

        Handler._online = True
        Handler._etag = etag
        fresh: dict[str, dict] = {}
        for entry in listing:
            name, sha = entry.get("name", ""), entry.get("sha")
            if not name.endswith(".json") or not sha:
                continue
            hit = Handler._cache.get(name)
            if hit and hit["sha"] == sha:
                fresh[name] = hit  # unchanged blob, no request
                continue
            st, blob, _ = self._api(
                f"https://api.github.com/repos/{repo}/contents/sessions/{name}?ref={branch}", tok
            )
            if st != 200 or not isinstance(blob, dict):
                if hit:
                    fresh[name] = hit
                continue
            try:
                rec = json.loads(base64.b64decode(blob.get("content", "")).decode())
            except (ValueError, UnicodeDecodeError):
                continue
            fresh[name] = {"sha": sha, "record": rec}
        Handler._cache = fresh
        Handler._last_good = [v["record"] for v in fresh.values()]
        return Handler._last_good

    def _records(self) -> tuple[list[dict], str]:
        recs = self._from_store()
        if recs is not None:
            return recs, ("store" if Handler._online else "store (stale)")
        local = self.state / "sessions"
        out = []
        for f in sorted(local.glob("*.json")):
            try:
                out.append(json.loads(f.read_text()))
            except (OSError, ValueError):
                continue
        return out, "local"

    def _snapshot(self) -> dict:
        recs, where = self._records()
        key = lambda r: r.get("attention_since") or r.get("last_seen") or ""

        waiting = sorted(
            (r for r in recs if r.get("needs_attention") and not r.get("ended")), key=key
        )  # oldest demand first
        running = sorted(
            (r for r in recs if not r.get("needs_attention") and not r.get("ended")),
            key=key,
            reverse=True,
        )
        recent = sorted((r for r in recs if r.get("ended")), key=key, reverse=True)[:15]

        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source": where,
            "counts": {"waiting": len(waiting), "running": len(running), "recent": len(recent)},
            "waiting": waiting,
            "running": running,
            "recent": recent,
        }

    # ---- http -------------------------------------------------------------
    def do_GET(self):
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


def serve_forever(port: int, state: Path) -> int:

    state.mkdir(parents=True, exist_ok=True)
    srv = HTTPServer(("127.0.0.1", port), partial(Handler, state=state))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0
