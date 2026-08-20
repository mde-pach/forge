#!/usr/bin/env python3
"""
Nothing changes the rules without a second pair of eyes.

There is a small set of files that decide how everything else behaves — hooks,
settings, plugin manifests, CI, context files. Editing those is how a gate gets
quietly disabled, and it is exactly where the session doing the editing is least
able to judge itself.

So: touch one of them, and the turn cannot end until an independent review of
that change has been recorded. Run on Stop, exit 2, which is the one exit code
that means "you are not finished".

The evidence for insisting on independence rather than care: asking a model to
critique its own output has been measured making accuracy *worse* — 5% to 3% on
one task — while the same model with a real external check reached 38%. Fresh
context is not a formality here, it is the entire mechanism.

The review is recorded by writing a file whose name fingerprints the reviewed
content; a subagent with fresh context produces it. Reviews expire when the
protected files change again, so one review cannot cover a later edit. The
file must quote, verbatim, the prompt the reviewer was given: independence the
guard cannot verify can at least be made auditable, and the one recorded review
that survived a real session turned out to have been handed its verdict in its
prompt ("found it sound overall ... trust this, don't re-derive it") - visible
only in a transcript nobody reads. Now it would be visible in the review.

This blocks, so it can loop. It did: one session attempted to end its turn 45
times in fourteen minutes, blocked identically every time, because its review
was running in the background and a blocked Stop is how you wait when waiting
is forbidden. The same release valve the gate uses applies here - after 3
consecutive blocks on the SAME outstanding fingerprint, the turn is released
once, loudly, and the guard re-arms - because a blocker that can spin forever
eventually will, at the worst moment. FORGE_GATE_NO_RELEASE disables the valve
where there is no human to unblock (CI), same as the gate.

This paragraph used to say `forge review` produces it. No such command has ever
existed - the registry declares three, and none of them is that. The message
this hook actually prints is self-contained and was always right; the docstring
was describing a command someone intended to build.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PROTECTED = (
    ".claude/settings.json",
    ".claude/hooks/",
    # A capability is what forge DOES when you ask it for something - closer to a
    # rule than to code, and the one thing here a session could quietly rewrite
    # mid-task to change its own instructions.
    ".claude/skills/",
    ".claude-plugin/",
    "plugins/",
    ".github/workflows/",
    "CLAUDE.md",
    ".claude/rules/",
    "pyproject.toml",
    "package.json",
)

REVIEW_DIR = ".claude/reviews"

# The loop-release valve, mirroring the gate's (.claude/.gate-state): counts
# consecutive blocks on one outstanding fingerprint. The fingerprint is already
# the digest - it identifies the exact demand being repeated - so unlike the
# gate there is nothing to normalise.
STATE = ".claude/.guard-state"
RELEASE_AFTER = 3


def _release(root: Path, fp: str) -> bool:
    """One more block on `fp`. True when this one should release instead."""
    if os.environ.get("FORGE_GATE_NO_RELEASE"):
        return False  # in CI a release would turn a red build green
    state = root / STATE
    try:
        prev, raw = state.read_text().split()
        count = int(raw)
    except (OSError, ValueError):
        prev, count = "", 0
    count = count + 1 if prev == fp else 1
    if count >= RELEASE_AFTER:
        state.unlink(missing_ok=True)  # re-arm: the next turn is guarded again
        return True
    try:
        state.write_text(f"{fp} {count}\n")
    except OSError:
        pass
    return False


def _clear(root: Path) -> None:
    (root / STATE).unlink(missing_ok=True)


def changed(root: Path) -> list[str]:
    try:
        r = subprocess.run(
            # -uall is load-bearing: without it git collapses a wholly-untracked
            # directory to one `?? .claude/` line, so a brand-new
            # .claude/settings.json is invisible - which is exactly how a hook or
            # a settings file first appears. The guard saw edits to existing
            # protected files and was blind to every new one.
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    out = []
    for line in r.stdout.splitlines():
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ")[-1]
        if any(path == p or path.startswith(p) for p in PROTECTED):
            out.append(path)
    return sorted(out)


def fingerprint(root: Path, files: list[str]) -> str:
    """Identifies the exact content under review, so a review cannot outlive it."""
    h = hashlib.sha256()
    for f in files:
        h.update(f.encode())
        try:
            h.update((root / f).read_bytes())
        except OSError:
            h.update(b"<missing>")
    return h.hexdigest()[:16]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    root = (
        Path(payload.get("cwd")) if isinstance(payload, dict) and payload.get("cwd") else Path.cwd()
    )

    files = changed(root)
    if not files:
        _clear(root)
        return 0

    fp = fingerprint(root, files)
    review = root / REVIEW_DIR / f"{fp}.md"
    if review.is_file():
        try:
            has_prompt = "## Prompt" in review.read_text(errors="replace")
        except OSError:
            has_prompt = False
        if has_prompt:
            _clear(root)
            return 0
        complaint = (
            f"A review exists at {REVIEW_DIR}/{fp}.md but it does not contain a"
            " `## Prompt` section\nquoting, verbatim, the prompt the reviewer was"
            " given. Without it there is no way to\naudit whether the reviewer was"
            " independent or was handed its verdict. Add the\nsection with the"
            " exact prompt used, or re-run the review and record both.\n"
        )
    else:
        complaint = (
            "This turn changed files that decide how everything else behaves:\n"
            + "".join(f"  {f}\n" for f in files)
            + "\nThese need an independent review before the turn can end — not a re-read by\n"
            "you, which is measurably worse than no review at all, but a fresh-context pass\n"
            "that has not seen the reasoning behind the change.\n\n"
            "Run a subagent IN THE FOREGROUND — wait for its result; do not launch a\n"
            "background reviewer and try to end the turn, that is a spin loop (measured\n"
            "once at 45 blocked stops). Give it the diff and the file list. Do NOT give\n"
            "it prior conclusions or the verdict you expect: a primed reviewer is worse\n"
            "than none. Then record its findings:\n"
            f"  mkdir -p {REVIEW_DIR} && write them to {REVIEW_DIR}/{fp}.md\n"
            "with a `## Prompt` section quoting, verbatim, the prompt the reviewer got.\n\n"
            "The name is a fingerprint of the reviewed content, so editing these files\n"
            "again invalidates the review rather than reusing it.\n"
        )

    if _release(root, fp):
        print(
            json.dumps(
                {
                    "systemMessage": (
                        "forge-guard released after "
                        f"{RELEASE_AFTER} identical blocks to avoid a loop - the "
                        "protected changes are NOT reviewed, and the guard re-arms "
                        "on the next turn."
                    )
                }
            )
        )
        return 0
    sys.stderr.write(complaint)
    return 2


if __name__ == "__main__":
    # SystemExit is a BaseException, so a bare `except BaseException` here
    # swallowed the exit(2) and turned every block into a pass. The gate printed
    # its refusal and let the turn end anyway - a gate that cannot block, which
    # is the exact failure this file exists to prevent, inside this file.
    try:
        code = main()
    except SystemExit:
        raise
    except Exception:
        code = 0
    sys.exit(code)
