"""
Run the session view.

One command brings the whole thing up: it says whether the view will actually
have anything to show and why not if it will not, serves the page on loopback,
and - if tailscale is here - makes it reachable from your phone, tearing that
down again when you stop it.

It used to be three commands (`serve`, `expose`, `doctor`) and a how-to page
telling you to run three scripts in the right order. `doctor` in particular was
a separate command you had to already know about to run when something looked
wrong; a readiness report you have to ask for is a report nobody reads. It runs
on the way up now, every time, and costs one conditional API request.

The readiness report never blocks. A view that shows only local records is
worth having, so a missing token degrades the page rather than refusing to
start - the opposite of forge's gates, deliberately, because this is a window
and not a gate.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

from forge.registry import ROOT

MONITOR = ROOT / "plugins" / "forge-monitor"
DEFAULT_PORT = 7373


def _load(filename: str) -> ModuleType:
    """Import a plugin module by path. The plugin is not on sys.path and must
    not be: it is loaded by Claude Code at launch, not installed.

    Spelled with the extension - `_load("serve.py")`, not `_load("serve")` -
    because the reachability check links files by name, and a stem assembled at
    runtime is a reference nothing can see."""
    path = MONITOR / filename
    name = path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        msg = f"cannot load {path}"
        raise ImportError(msg)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


def _readiness(serve: ModuleType, state: Path) -> None:
    """What the view will be able to show, and the reason when the answer is
    'less than you expect'. Prints; never raises, never exits."""
    print("readiness")
    local = len(list((state / "sessions").glob("*.json"))) if (state / "sessions").is_dir() else 0
    print(f"  state      {state} ({local} local record(s))")

    cfg = serve.load_config(state)
    repo = (cfg.get("store") or {}).get("repo")
    branch = (cfg.get("store") or {}).get("branch", "main")
    if not repo:
        print("  store      not configured - this machine's sessions only.")
        print("             see docs/how-to/monitor.md to publish them")
        return

    tok = serve.find_token(cfg)
    if not tok:
        print(f"  store      {repo} configured, but no token was found.")
        print("             tried FORGE_MONITOR_TOKEN, GH_TOKEN, GITHUB_TOKEN, `gh auth token`")
        print("             the view falls back to this machine's records")
        return

    status, listing, _ = serve.api(
        f"https://api.github.com/repos/{repo}/contents/sessions?ref={branch}", tok
    )
    if status == 200 and isinstance(listing, list):
        print(f"  store      {repo}@{branch} - {len(listing)} session record(s)")
    elif status == 404:
        print(f"  store      {repo}@{branch} reachable, no sessions published yet")
    elif status == 403:
        print(f"  store      {repo} refused the token (403). Not retrying with a broader scope.")
        print("             the token needs `contents` on that repository, nothing more")
    elif status == 0:
        print(f"  store      {repo} unreachable (network). Showing the last state read")
    else:
        print(f"  store      {repo} answered {status}. Showing the last state read")


def _tailscale(port: int) -> str | None:
    """Expose on the tailnet, returning the URL. None if that is not possible,
    which is normal and not an error."""
    if not shutil.which("tailscale"):
        return None
    script = MONITOR / "tailscale" / "expose.sh"
    r = subprocess.run(
        ["sh", str(script), "on", str(port)], capture_output=True, text=True, check=False
    )
    if r.returncode != 0:
        detail = (r.stderr or r.stdout or "").strip().splitlines()
        print(f"  tailnet    not exposed: {detail[-1] if detail else 'expose failed'}")
        return None
    return (r.stdout or "").strip() or ""


def _unexpose(port: int) -> None:
    script = MONITOR / "tailscale" / "expose.sh"
    subprocess.run(
        ["sh", str(script), "off", str(port)], capture_output=True, text=True, check=False
    )


def run(args: Sequence[str] = ()) -> int:
    ap = argparse.ArgumentParser(prog="forge start")
    ap.add_argument(
        "--port", type=int, default=int(os.environ.get("FORGE_MONITOR_PORT") or DEFAULT_PORT)
    )
    ap.add_argument("--state", default=None, help="override the state directory")
    ap.add_argument(
        "--local-only",
        action="store_true",
        help="do not expose on the tailnet even if it is set up",
    )
    opts = ap.parse_args(list(args))

    paths = _load("paths.py")
    serve = _load("serve.py")
    state = Path(opts.state) if opts.state else paths.state_dir()
    state.mkdir(parents=True, exist_ok=True)

    _readiness(serve, state)

    print("\nreach")
    print(f"  local      http://127.0.0.1:{opts.port}")
    exposed = None if opts.local_only else _tailscale(opts.port)
    if exposed:
        print(f"  tailnet    {exposed}")
        print("             open it on your phone and add it to the home screen")
    elif exposed == "":
        print("  tailnet    exposed - `tailscale serve status` for the URL")
    elif not opts.local_only and not shutil.which("tailscale"):
        print("  tailnet    tailscale is not installed, so this is loopback only")

    print("\nctrl-c to stop")
    try:
        return serve.serve_forever(opts.port, state)
    finally:
        if exposed is not None:
            _unexpose(opts.port)
