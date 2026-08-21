#!/usr/bin/env python3
"""PreToolUse hook on Write/Edit: a file may not get denser in prose.

An edit is compared to the file as it is; a new file to the median of its kind
at HEAD. Up to TOLERANCE denser passes with a warning; beyond it is refused.
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import statistics
import subprocess
import sys
import tokenize
from pathlib import Path

KINDS = {".py": "py", ".sh": "sh", ".bash": "sh", ".md": "md"}
TOLERANCE = 0.05
SKIP = ("stacks/", ".claude/reviews/")


def _py_words(src: str) -> int:
    words = 0
    try:
        for t in tokenize.generate_tokens(io.StringIO(src).readline):
            if t.type == tokenize.COMMENT:
                words += len(t.string.lstrip("#").split())
    except (tokenize.TokenError, SyntaxError):
        pass
    try:
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                d = ast.get_docstring(n)
                if d:
                    words += len(d.split())
    except SyntaxError:
        pass
    return words


def _sh_words(src: str) -> int:
    return sum(
        len(line.lstrip("#").split())
        for line in src.splitlines()
        if line.strip().startswith("#") and not line.startswith("#!")
    )


def _code_lines(src: str) -> int:
    return sum(1 for line in src.splitlines() if line.strip() and not line.strip().startswith("#"))


def density(path: str, src: str) -> float | None:
    """py/sh: prose words per code line. md: mean words per paragraph."""
    kind = KINDS.get(Path(path).suffix)
    if kind is None or any(s in path for s in SKIP):
        return None
    if kind == "md":
        body = re.sub(r"```.*?```", "", src, flags=re.DOTALL)
        paras = [
            p
            for p in re.split(r"\n\s*\n", body)
            if p.strip() and not re.match(r"[#|>*-]|\d+\.", p.lstrip())
        ]
        return statistics.mean(len(p.split()) for p in paras) if paras else 0.0
    code = _code_lines(src)
    words = _py_words(src) if kind == "py" else _sh_words(src)
    return words / code if code else 0.0


def _root(path: Path) -> Path | None:
    for p in [path, *path.parents]:
        if (p / ".git").exists():
            return p
    return None


def tree_densities(root: Path, kind: str) -> dict[str, float]:
    """Density of every tracked file of `kind` at HEAD."""
    out: dict[str, float] = {}
    try:
        files = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.split()
    except (subprocess.SubprocessError, OSError):
        return out
    for f in files:
        if KINDS.get(Path(f).suffix) != kind:
            continue
        try:
            src = subprocess.run(
                ["git", "-C", str(root), "show", f"HEAD:{f}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            ).stdout
        except (subprocess.SubprocessError, OSError, UnicodeDecodeError):
            continue
        d = density(f, src)
        if d is not None:
            out[f] = d
    return out


def reference(path: Path) -> float | None:
    root = _root(path)
    if root is None:
        return None
    values = list(tree_densities(root, KINDS[path.suffix]).values())
    return statistics.median(values) if values else None


def proposed(tool: str, inp: dict[str, object]) -> tuple[str, str, str | None] | None:
    path = inp.get("file_path")
    if not isinstance(path, str):
        return None
    try:
        current = Path(path).read_text()
    except (OSError, UnicodeDecodeError):
        current = None
    if tool == "Write":
        content = inp.get("content")
        return (path, content, current) if isinstance(content, str) else None
    if tool == "Edit" and current is not None:
        old, new = inp.get("old_string"), inp.get("new_string")
        if not isinstance(old, str) or not isinstance(new, str):
            return None
        n = -1 if inp.get("replace_all") else 1
        return path, current.replace(old, new, n), current
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") not in ("Write", "Edit"):
        return 0
    p = proposed(payload["tool_name"], payload.get("tool_input") or {})
    if p is None:
        return 0
    path, new, current = p
    after = density(path, new)
    if after is None:
        return 0
    before = density(path, current) if current is not None else reference(Path(path))
    if before is None or after <= before + 1e-9:
        return 0
    what = "was" if current is not None else "tree median"
    where = f"{os.path.relpath(path)}: density {after:.2f}, {what} {before:.2f}"
    if after <= before * (1 + TOLERANCE):
        print(json.dumps({"systemMessage": f"{where}. Within tolerance; a signal, not a fault."}))
        return 0
    sys.stderr.write(f"{where}. Refused.\n")
    return 2


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit:
        raise
    except Exception:
        code = 0
    sys.exit(code)
