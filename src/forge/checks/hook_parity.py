"""
The settings file and the plugin manifests must tell the same story.

Forge's process rides in the repo: `.claude/settings.json` registers the
monitor's hooks against the working tree and the guard's hooks against
`origin/main`, while the plugin manifests remain the projection every other
surface installs. That is one mechanism published twice, and the two copies
have no compiler keeping them equal - the monitor's eleven events were
hand-transcribed once, and the first independent review of that transcription
flagged exactly this; the second review flagged that the guard's side of the
comparison was a substring match pretending to be one.

So this check is that compiler, and it must hold four things:

  1. every monitor event in the manifest fires identically from settings
     (exactly once - a duplicated entry is a double-fire, not a match);
  2. settings fire no monitor event the manifest does not declare;
  3. every guard event in the guard's manifest runs the byte-exact pinned
     runner - synchronously, because an async guard cannot block, which makes
     `"async": true` on a guard entry the single most damaging one-line edit
     available against this wiring;
  4. the pinned copy and the tree copy of each guard script are identical.
     Between editing guard code and pushing it, they are not - the enforcing
     copy is then older than the tree, possibly missing a fix. That window is
     inherent to pinning; this rule makes it red instead of silent.

Why the guard is pinned and the monitor is not, in one sentence each: the
monitor fails open and a session corrupting its own telemetry is a bounded,
accepted harm; the guard fails closed and must not be judged by the very tree
it is judging, so it runs the last fetched, pushed, reviewed version of itself.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from forge.registry import ROOT

MONITOR_MANIFEST = "plugins/forge-monitor/hooks/hooks.json"
GUARD_MANIFEST = "plugins/forge-guard/hooks/hooks.json"
SETTINGS = ".claude/settings.json"
EMIT = "${CLAUDE_PROJECT_DIR}/plugins/forge-monitor/hooks/emit.sh"

# The guard event -> the script the pinned runner must extract, derived from
# the guard manifest's own args at check time; this table only maps the
# launcher-relative name to the repo path the pinned form needs.
GUARD_DIR = "plugins/forge-guard/hooks"


def pinned_script(script: str) -> str:
    """The inline runner, byte-exact: the settings copy must equal this string,
    and the check makes any divergence red (settings were written from it once;
    no generator survives in the tree, the equality rule is the generator's
    replacement).

    Behavior: extract the guard script as of origin/main and run it with the
    hook payload still on stdin, propagating its exit code. Every path that
    cannot run the pinned copy exits 0 but says WHICH capability was missing -
    a systemMessage on stdout, because an invisible fail-open on a fail-closed
    mechanism is how a guard vanishes, and a wrong diagnosis in that message
    wastes the human it was written for. Open rather than closed on failure,
    because blocking every turn in every tarball checkout forever is worse.
    The temp file can leak if the harness kills the hook mid-run; accepted.
    Note the window this pins into existence: between editing guard code and
    pushing it, the enforcing copy is missing exactly those edits - including,
    until they land, their fixes.
    """
    path = f"{GUARD_DIR}/{script}"
    off = "printf '{\"systemMessage\":\"forge-guard is OFF in this checkout: %s.\"}\\n'"
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


def _load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _flat(hooks_cfg: dict) -> list[tuple[str, dict]]:
    """Every (event, hook-entry) pair, flattened out of the two-level nesting.
    Malformed shapes are skipped, not raised on: a checker that crashes on bad
    input masks every check after it and reports nothing about this one."""
    out = []
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


def _script_of(hook: dict) -> str | None:
    """The launcher-relative script name from a guard-manifest entry, or None
    when the args are not the two-element [runner, script] shape."""
    args = hook.get("args")
    if isinstance(args, list) and len(args) >= 2 and isinstance(args[1], str):
        return args[1]
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


def drift(reader=_pinned_blob) -> list[str]:
    """Rule 4: the enforcing copy equals the tree copy, script by script."""
    errs = []
    manifest = _load(ROOT / GUARD_MANIFEST) or {}
    for _event, hook in _flat(manifest.get("hooks") or {}):
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
                f"{path}: the enforcing origin/main copy differs from the tree copy - "
                "the guard that runs is not the guard you are reading; push to close the window"
            )
    return errs


def check(settings: dict | None = None, manifest: dict | None = None,
          guard_manifest: dict | None = None) -> list[str]:
    """Rules 1-3. Injectable inputs exist so the proofs can break them."""
    if settings is None:
        settings = _load(ROOT / SETTINGS)
    if manifest is None:
        manifest = _load(ROOT / MONITOR_MANIFEST)
    if guard_manifest is None:
        guard_manifest = _load(ROOT / GUARD_MANIFEST)
    if settings is None:
        return [f"{SETTINGS} is missing or not valid JSON"]
    if manifest is None:
        return [f"{MONITOR_MANIFEST} is missing or not valid JSON"]
    if guard_manifest is None:
        return [f"{GUARD_MANIFEST} is missing or not valid JSON"]

    errs: list[str] = []
    flat = _flat(settings.get("hooks") or {})

    # 1. Every monitor event in the manifest fires identically, exactly once.
    for event, mhook in _flat(manifest.get("hooks") or {}):
        want_args = [EMIT, event]
        matches = [h for e, h in flat if e == event and h.get("args") == want_args]
        if not matches:
            errs.append(f"monitor event {event} is in the manifest but not in {SETTINGS}")
            continue
        if len(matches) > 1:
            errs.append(f"monitor event {event} fires {len(matches)} times from {SETTINGS}")
        for s in matches:
            for field in ("timeout", "async"):
                if s.get(field) != mhook.get(field):
                    errs.append(
                        f"monitor event {event}: settings {field}={s.get(field)!r} "
                        f"but manifest says {mhook.get(field)!r}"
                    )
            if s.get("command") != mhook.get("command") or s.get("type") != mhook.get("type"):
                errs.append(
                    f"monitor event {event}: settings run it as "
                    f"{s.get('type')!r}/{s.get('command')!r} but the manifest says "
                    f"{mhook.get('type')!r}/{mhook.get('command')!r}"
                )

    # 2. No monitor event fires from settings that the manifest does not declare.
    manifest_events = {e for e, _ in _flat(manifest.get("hooks") or {})}
    for event, h in flat:
        args = h.get("args") or []
        if any(str(a).endswith("emit.sh") for a in args) and event not in manifest_events:
            errs.append(f"settings fires monitor event {event} that the manifest does not declare")

    # 3. Every guard event runs the byte-exact pinned runner, synchronously.
    guard_pairs = set()
    for event, ghook in _flat(guard_manifest.get("hooks") or {}):
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
                errs.append(
                    f"guard event {event} is async - an async guard cannot block, so it is not a guard"
                )
            if s.get("timeout") != ghook.get("timeout"):
                errs.append(
                    f"guard event {event}: settings timeout={s.get('timeout')!r} "
                    f"but manifest says {ghook.get('timeout')!r}"
                )

    # 3b. The other direction: no settings entry runs a pinned guard script the
    # guard manifest does not declare. A ghost guard entry is drift too - the
    # manifest drops an event, settings keep enforcing it, and the two published
    # copies of the wiring quietly tell different stories.
    marker = f"origin/main:{GUARD_DIR}/"
    for event, h in flat:
        args = h.get("args") or []
        joined = " ".join(str(a) for a in args)
        if marker not in joined:
            continue
        scripts = {s for _e, s in guard_pairs}
        named = next((s for s in scripts if f"{marker}{s} " in joined or joined.endswith(f"{marker}{s}")), None)
        if (event, named) not in guard_pairs:
            errs.append(
                f"settings fire a pinned guard runner on {event} that the guard manifest does not declare"
            )

    # 4. The marketplace copies are off, so nothing fires twice in this repo.
    enabled = settings.get("enabledPlugins") or {}
    for plugin in ("forge-monitor@forge", "forge-guard@forge"):
        if enabled.get(plugin) is not False:
            errs.append(f"{plugin} is not disabled in {SETTINGS}; both copies would fire")

    return errs
