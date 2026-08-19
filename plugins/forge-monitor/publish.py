#!/usr/bin/env python3
"""
Publish session records to the store, over the GitHub API.

There is no clone. Nothing here needs git's semantics: one session owns one
path, so an update is a single PUT carrying that file's blob sha. That removes
the working copy from every machine, the commit, the rebase-and-retry loop, and
git itself from the hook path - while keeping the history, because every PUT is
still a commit.

    publish.py <session-id>   publish one record
    publish.py --flush        publish every record the store is behind on

Never raises, never prints to stdout, always exits 0. It runs inside a hook.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.github.com"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_dir() -> Path:
    return Path(
        os.environ.get("FORGE_MONITOR_STATE")
        or Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "forge-monitor"
    )


def config(state: Path) -> dict:
    try:
        return json.loads((state / "config.json").read_text())
    except (OSError, ValueError):
        return {}


def token(cfg: dict) -> str | None:
    """Nothing is stored by us in the first two cases."""
    for var in ("FORGE_MONITOR_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                           timeout=10, check=False)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        pass
    tf = (cfg.get("store") or {}).get("token_file")
    if tf:
        try:
            return Path(os.path.expanduser(tf)).read_text().strip() or None
        except OSError:
            pass
    return None


def call(method: str, url: str, tok: str, body: dict | None = None,
         timeout: int = 20) -> tuple[int, dict, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "forge-monitor")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {}), dict(r.headers)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}"), dict(e.headers)
        except (ValueError, OSError):
            return e.code, {}, {}
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return 0, {}, {}


def write_record(path: Path, rec: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, indent=2))
    tmp.replace(path)  # atomic: a reader never sees half a record


def publish_one(state: Path, cfg: dict, tok: str, sid: str) -> bool:
    f = state / "sessions" / f"{sid}.json"
    try:
        rec = json.loads(f.read_text())
    except (OSError, ValueError):
        return False

    store = cfg.get("store") or {}
    repo, branch = store.get("repo"), store.get("branch", "main")
    if not repo:
        return False

    path = f"sessions/{sid}.json"
    url = f"{API}/repos/{repo}/contents/{path}"
    payload = dict(rec)
    payload.pop("store_sha", None)          # bookkeeping, not state
    payload.pop("publish_attempted_at", None)

    body = {
        "message": f"{rec.get('project') or 'session'} {sid[:8]}: {rec.get('state', '?')}"
                   + (f" ({rec['attention_reason']})" if rec.get("attention_reason") else ""),
        "content": base64.b64encode(
            (json.dumps(payload, indent=2) + "\n").encode()).decode(),
        "branch": branch,
    }
    if rec.get("store_sha"):
        body["sha"] = rec["store_sha"]

    status, resp, _ = call("PUT", url, tok, body)

    # 409/422 mean our cached sha is stale - somebody (a re-clone, a manual
    # edit) moved the file. Ask once what the sha is now, then retry. This is
    # the only concurrency case that exists, because one session owns one path.
    if status in (409, 422):
        st2, cur, _ = call("GET", f"{url}?ref={branch}", tok)
        if st2 == 200 and cur.get("sha"):
            body["sha"] = cur["sha"]
            status, resp, _ = call("PUT", url, tok, body)
        elif st2 == 404:
            body.pop("sha", None)           # it is gone; create it fresh
            status, resp, _ = call("PUT", url, tok, body)

    if status in (200, 201):
        rec["published_at"] = now()
        sha = ((resp.get("content") or {}).get("sha"))
        if sha:
            rec["store_sha"] = sha
        write_record(f, rec)
        return True
    return False


def pending(state: Path) -> list[str]:
    """Records the store is behind on: never published, or changed since.

    This is what makes retry a property rather than a special case - a push
    that failed while offline is simply still pending, and the next event on
    this machine flushes it.
    """
    out = []
    d = state / "sessions"
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.json")):
        try:
            rec = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if (rec.get("published_at") or "") < (rec.get("last_seen") or ""):
            out.append(f.stem)
    return out


def main() -> int:
    args = sys.argv[1:]
    state = state_dir()
    cfg = config(state)
    if not (cfg.get("store") or {}).get("repo"):
        return 0
    tok = token(cfg)
    if not tok:
        return 0

    if args and args[0] == "--flush":
        for sid in pending(state)[:25]:      # bounded: a hook is not a batch job
            publish_one(state, cfg, tok, sid)
        return 0

    if args:
        publish_one(state, cfg, tok, args[0])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:                    # a monitor never takes the session with it
        raise SystemExit(0)
