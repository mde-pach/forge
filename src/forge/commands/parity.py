"""
Does the remote hold exactly what this checkout holds?

Pushes go through the GitHub API rather than `git push`, so the remote is
hand-assembled and there is nothing that notices when it drifts. It drifted
twice: `package-lock.json` was never pushed at all, and a stale
`repo-admin/manifest.yaml` sat on the remote for two days. Both were found by
accident, and this repo has recorded "the mirror is not re-runnable" as an open
friction since Monday while I re-checked it by hand each time.

Git blob SHAs are content-addressed the same way on both sides, so the
comparison is exact rather than heuristic — no diffing, no sampling.

File modes are reported separately: the contents API cannot write an exec bit,
so a mode difference is expected and is not content drift. Hooks are invoked as
`sh <script>` precisely so that does not matter.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence

from forge.registry import ROOT

API = "https://api.github.com"
DEFAULT_REPO = "mde-pach/forge"


def _token() -> str | None:
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
        return None
    return None


def _local() -> dict[str, tuple[str, str]]:
    """path -> (blob sha, mode)"""
    r = subprocess.run(
        ["git", "ls-files", "-s"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    out: dict[str, tuple[str, str]] = {}
    for line in r.stdout.splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) >= 2 and path:
            out[path] = (parts[1], parts[0])
    return out


def _remote(repo: str, branch: str, token: str) -> dict[str, tuple[str, str]] | str:
    url = f"{API}/repos/{repo}/git/trees/{branch}?recursive=1"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "forge-parity")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} from the tree API"
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        return f"could not reach the tree API: {e}"
    if data.get("truncated"):
        return "the tree response was truncated; this repo is too large for one request"
    return {
        n["path"]: (n["sha"], n.get("mode", "?"))
        for n in data.get("tree", [])
        if n.get("type") == "blob"
    }


def run(args: Sequence[str] = ()) -> int:
    repo = args[0] if args else os.environ.get("FORGE_REPO", DEFAULT_REPO)
    branch = args[1] if len(args) > 1 else "main"

    token = _token()
    if not token:
        print("parity: no credential. Run `gh auth login`, or set GH_TOKEN.", file=sys.stderr)
        return 2

    remote = _remote(repo, branch, token)
    if isinstance(remote, str):
        print(f"parity: {remote}", file=sys.stderr)
        return 2

    local = _local()
    missing = sorted(set(local) - set(remote))
    extra = sorted(set(remote) - set(local))
    differing = sorted(p for p in set(local) & set(remote) if local[p][0] != remote[p][0])
    mode_only = [p for p in set(local) & set(remote) if local[p][1] != remote[p][1]]

    for p in missing:
        print(f"  MISSING on {branch}   {p}")
    for p in extra:
        print(f"  EXTRA on {branch}     {p}")
    for p in differing:
        print(f"  DIFFERS              {p}")

    matched = len(local) - len(missing) - len(differing)
    print(f"{matched}/{len(local)} files identical on {repo}@{branch}")
    if mode_only:
        print(f"{len(mode_only)} file(s) differ only in mode — expected: the contents API")
        print("cannot write an exec bit, which is why hooks are invoked as `sh <script>`.")

    return 1 if (missing or extra or differing) else 0
