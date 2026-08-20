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
protected files change again, so one review cannot cover a later edit.

This paragraph used to say `forge review` produces it. No such command has ever
existed - the registry declares three, and none of them is that. The message
this hook actually prints is self-contained and was always right; the docstring
was describing a command someone intended to build.
"""

from __future__ import annotations

import hashlib
import json
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
        return 0

    fp = fingerprint(root, files)
    if (root / REVIEW_DIR / f"{fp}.md").is_file():
        return 0

    sys.stderr.write(
        "This turn changed files that decide how everything else behaves:\n"
        + "".join(f"  {f}\n" for f in files)
        + "\nThese need an independent review before the turn can end — not a re-read by\n"
        "you, which is measurably worse than no review at all, but a fresh-context pass\n"
        "that has not seen the reasoning behind the change.\n\n"
        "Run a subagent to review the diff of exactly these files, then record it:\n"
        f"  mkdir -p {REVIEW_DIR} && write the findings to {REVIEW_DIR}/{fp}.md\n\n"
        "The name is a fingerprint of the reviewed content, so editing these files\n"
        "again invalidates the review rather than reusing it.\n"
    )
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
