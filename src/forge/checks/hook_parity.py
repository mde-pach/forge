"""`.claude/settings.json` fires exactly what the plugin manifests declare.

1. each monitor event fires from settings identically, once; 2. no undeclared
monitor event fires; 3. each guard event runs the byte-exact pinned runner,
synchronously, and no undeclared one fires; 4. origin/main and tree copies of
each guard script are equal. Pinning keeps the guard from judging itself.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from forge.registry import ROOT

MONITOR_MANIFEST = "plugins/forge-monitor/hooks/hooks.json"
GUARD_MANIFEST = "plugins/forge-guard/hooks/hooks.json"
SETTINGS = ".claude/settings.json"
EMIT = "${CLAUDE_PROJECT_DIR}/plugins/forge-monitor/hooks/emit.sh"
GUARD_DIR = "plugins/forge-guard/hooks"
PLUGINS = ("forge-monitor@forge", "forge-guard@forge")

Hook = dict[str, Any]


def pinned_script(script: str) -> str:
    """Inline runner: extract the script from origin/main and run it; if it cannot, exit 0 and say why."""
    path = f"{GUARD_DIR}/{script}"
    off = 'printf \'{"systemMessage":"forge-guard is OFF in this checkout: %s."}\\n\''
    return (
        f"t=$(mktemp) || {{ {off % 'mktemp failed'}; exit 0; }}; "
        f'if git -C "${{CLAUDE_PROJECT_DIR:-.}}" show origin/main:{path} >"$t" 2>/dev/null; then '
        "for py in python3 python py; do "
        'if command -v "$py" >/dev/null 2>&1; then "$py" "$t"; rc=$?; rm -f "$t"; exit $rc; fi; '
        "done; "
        f'rm -f "$t"; {off % "no python interpreter found"}; exit 0; '
        f"fi; "
        f'rm -f "$t"; '
        f"{off % f'origin/main:{path} is not extractable (no git, no origin remote, or a shallow clone)'}; "
        "exit 0"
    )


def _load(path: Path) -> Hook | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _flat(hooks_cfg: Hook | None) -> list[tuple[str, Hook]]:

    out: list[tuple[str, Hook]] = []
    for event, groups in (hooks_cfg or {}).items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            for hook in group.get("hooks") or []:
                if isinstance(hook, dict):
                    out.append((event, hook))
    return out


def _script_of(hook: Hook) -> str | None:
    args = hook.get("args")
    if isinstance(args, list) and len(args) >= 2 and isinstance(args[1], str):
        return str(args[1])
    return None


def _pinned_blob(path: str) -> bytes | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"origin/main:{path}"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return r.stdout if r.returncode == 0 else None


def drift(reader: Callable[[str], bytes | None] = _pinned_blob) -> list[str]:
    """Rule 4."""
    errs = []
    manifest = _load(ROOT / GUARD_MANIFEST) or {}
    for _event, hook in _flat(manifest.get("hooks")):
        script = _script_of(hook)
        if not script:
            continue
        path = f"{GUARD_DIR}/{script}"
        pinned = reader(path)
        try:
            tree = (ROOT / path).read_bytes()
        except OSError:
            errs.append(f"{path}: the tree copy is missing or unreadable")
            continue
        if pinned is None:
            errs.append(f"{path}: the pinned origin/main copy is not extractable here")
        elif pinned != tree:
            errs.append(
                f"{path}: the enforcing origin/main copy differs from the tree copy - push to close the window"
            )
    return errs


def check(
    settings: Hook | None = None,
    manifest: Hook | None = None,
    guard_manifest: Hook | None = None,
) -> list[str]:
    """Rules 1-3."""
    settings = _load(ROOT / SETTINGS) if settings is None else settings
    manifest = _load(ROOT / MONITOR_MANIFEST) if manifest is None else manifest
    guard_manifest = _load(ROOT / GUARD_MANIFEST) if guard_manifest is None else guard_manifest
    if settings is None:
        return [f"{SETTINGS} is missing or not valid JSON"]
    if manifest is None:
        return [f"{MONITOR_MANIFEST} is missing or not valid JSON"]
    if guard_manifest is None:
        return [f"{GUARD_MANIFEST} is missing or not valid JSON"]

    errs: list[str] = []
    flat = _flat(settings.get("hooks"))

    # 1.
    for event, mhook in _flat(manifest.get("hooks")):
        matches = [h for e, h in flat if e == event and h.get("args") == [EMIT, event]]
        if not matches:
            errs.append(f"monitor event {event} is in the manifest but not in {SETTINGS}")
            continue
        if len(matches) > 1:
            errs.append(f"monitor event {event} fires {len(matches)} times from {SETTINGS}")
        for s in matches:
            for field in ("timeout", "async", "command", "type"):
                if s.get(field) != mhook.get(field):
                    errs.append(
                        f"monitor event {event}: settings {field}={s.get(field)!r} "
                        f"but manifest says {mhook.get(field)!r}"
                    )

    # 2.
    manifest_events = {e for e, _ in _flat(manifest.get("hooks"))}
    for event, h in flat:
        if (
            any(str(a).endswith("emit.sh") for a in h.get("args") or [])
            and event not in manifest_events
        ):
            errs.append(f"settings fires monitor event {event} that the manifest does not declare")

    # 3.
    guard_pairs: set[tuple[str, str]] = set()
    for event, ghook in _flat(guard_manifest.get("hooks")):
        script = _script_of(ghook)
        if not script:
            errs.append(f"guard manifest event {event} has malformed args; cannot verify it")
            continue
        guard_pairs.add((event, script))
        want = ["-c", pinned_script(script)]
        matches = [h for e, h in flat if e == event and h.get("args") == want]
        if not matches:
            errs.append(
                f"guard event {event} does not run the byte-exact pinned runner for {script}"
            )
            continue
        if len(matches) > 1:
            errs.append(f"guard event {event} fires {len(matches)} times from {SETTINGS}")
        for s in matches:
            if s.get("command") != "sh":
                errs.append(f"guard event {event}: command is {s.get('command')!r}, not sh")
            if s.get("async"):
                errs.append(f"guard event {event} is an async guard - it cannot block")
            if s.get("timeout") != ghook.get("timeout"):
                errs.append(
                    f"guard event {event}: settings timeout={s.get('timeout')!r} "
                    f"but manifest says {ghook.get('timeout')!r}"
                )

    marker = f"origin/main:{GUARD_DIR}/"
    scripts = {s for _e, s in guard_pairs}
    for event, h in flat:
        joined = " ".join(str(a) for a in h.get("args") or [])
        if marker not in joined:
            continue
        named = next(
            (s for s in scripts if f"{marker}{s} " in joined or joined.endswith(f"{marker}{s}")),
            None,
        )
        if named is None or (event, named) not in guard_pairs:
            errs.append(
                f"settings fire a pinned guard runner on {event} that the guard manifest does not declare"
            )

    # Marketplace copies off, or each hook fires twice.
    enabled = settings.get("enabledPlugins") or {}
    for plugin in PLUGINS:
        if enabled.get(plugin) is not False:
            errs.append(f"{plugin} is not disabled in {SETTINGS}; both copies would fire")

    return errs
