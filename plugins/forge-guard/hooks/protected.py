#!/usr/bin/env python3
"""Stop hook: changed protected files need a recorded independent review before the turn ends.

The review file is named by a fingerprint of the changed content and must quote
the reviewer's prompt. RELEASE_AFTER identical blocks release once, loudly.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# Everything that decides behaviour; docs/, README.md and lockfiles stay exposed.
PROTECTED = (
    ".claude/",
    ".claude-plugin/",
    "plugins/",
    ".github/",
    "CLAUDE.md",
    "pyproject.toml",
    "package.json",
    ".gitignore",
    "src/forge/",
    "kernel/",
    "contract/",
    "stacks/",
)

# Written during a Stop; counting them would seal the release valve.
EXEMPT = (".claude/reviews/", ".claude/.guard-state", ".claude/.gate-state")

REVIEW_DIR = ".claude/reviews"
STATE = ".claude/.guard-state"
RELEASE_AFTER = 3


def _release(root: Path, fp: str) -> bool:

    if os.environ.get("FORGE_GATE_NO_RELEASE"):
        return False
    state = root / STATE
    try:
        prev, raw = state.read_text().split()
        count = int(raw)
    except (OSError, ValueError):
        prev, count = "", 0
    count = count + 1 if prev == fp else 1
    if count >= RELEASE_AFTER:
        state.unlink(missing_ok=True)
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
            # -uall: a new directory must not collapse to one line; -z: no C-quoting.
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    out = []
    entries = r.stdout.split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        if status[:1] in ("R", "C"):
            i += 1  # skip the rename source
        if path.startswith(EXEMPT):
            continue
        if "/.claude/" in path or any(path == p or path.startswith(p) for p in PROTECTED):
            out.append(path)
    return sorted(out)


def fingerprint(root: Path, files: list[str]) -> str:
    h = hashlib.sha256()
    for f in files:
        h.update(f.encode() + b"\0")
        try:
            h.update((root / f).read_bytes())
        except OSError:
            h.update(b"<missing>")
        h.update(b"\0")
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
        complaint = f"{REVIEW_DIR}/{fp}.md lacks a `## Prompt` section quoting the reviewer's prompt verbatim.\n"
    else:
        complaint = (
            "Protected files changed; an independent review is required before the turn ends:\n"
            + "".join(f"  {f}\n" for f in files)
            + "If a reviewer is ALREADY running: TaskOutput(task_id=<id>, block=true, timeout=600000).\n"
            "Else: Agent(prompt=<file list and how to see the diff; no prior conclusions, no expected verdict>)\n"
            "then the same TaskOutput wait. Never poll, never end the turn while it runs.\n"
            f"Record findings in {REVIEW_DIR}/{fp}.md with a `## Prompt` section quoting the prompt verbatim.\n"
        )

    if _release(root, fp):
        print(
            json.dumps(
                {
                    "systemMessage": (
                        f"forge-guard released after {RELEASE_AFTER} identical blocks; "
                        "changes are NOT reviewed; re-arms next turn."
                    )
                }
            )
        )
        return 0
    sys.stderr.write(complaint)
    return 2


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit:
        raise
    except Exception:
        code = 0
    sys.exit(code)
