#!/usr/bin/env python3
"""
Tell the session what already exists, before it builds a second one.

Runs on UserPromptSubmit, one of only three events whose stdout Claude Code adds
to the model's context. That is the whole mechanism: at the moment you ask for
something, the list of what is already here arrives with your request.

Why this is worth a hook rather than a note in a document: measured on real
AI-authored pull requests, agents produce 1.87x the redundancy of human ones and
delete about a third as much code. Not because the model prefers duplication,
but because what already exists is not in front of it. This puts it there.

Silent unless it has something to say, and never blocks.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def registry_summary(root: Path) -> list[str]:
    """The declared entry points of whatever this project is."""
    out: list[str] = []

    py = root / "pyproject.toml"
    if py.is_file():
        try:
            import tomllib

            data = tomllib.loads(py.read_text())
            for name in data.get("project", {}).get("scripts") or {}:
                out.append(f"uv run {name}")
        except Exception:
            pass

    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text())
            runner = "bun run" if data.get("packageManager", "").startswith("bun") else "npm run"
            out += [f"{runner} {name}" for name in (data.get("scripts") or {})]
        except (OSError, ValueError):
            pass
    return out


def existing_files(root: Path) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, timeout=10, check=False
        )
        return [f for f in r.stdout.splitlines() if f]
    except (subprocess.SubprocessError, OSError):
        return []


def relevant(prompt: str, files: list[str], limit: int = 12) -> list[str]:
    """Files whose name shares a meaningful word with the request."""
    words = {
        w for w in "".join(c if c.isalnum() else " " for c in prompt.lower()).split() if len(w) > 3
    }
    if not words:
        return []
    scored = []
    for f in files:
        stem = Path(f).stem.lower().replace("-", " ").replace("_", " ")
        hits = sum(1 for w in words if w in stem or stem in w)
        if hits:
            scored.append((hits, f))
    scored.sort(reverse=True)
    return [f for _, f in scored[:limit]]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0

    root = Path(payload.get("cwd") or Path.cwd())
    prompt = str(payload.get("prompt") or payload.get("user_prompt") or "")

    entries = registry_summary(root)
    matches = relevant(prompt, existing_files(root))
    if not entries and not matches:
        return 0

    lines = ["<what-already-exists>"]
    if entries:
        lines.append(
            "Declared entry points — everything runnable is one of these, "
            "and adding a second way to do one of these jobs is a defect:"
        )
        lines += [f"  {e}" for e in sorted(entries)]
    if matches:
        lines.append("Existing files related to this request:")
        lines += [f"  {m}" for m in matches]
    lines.append("Prefer changing one of these to adding something beside it.")
    lines.append("</what-already-exists>")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass
    sys.exit(0)
