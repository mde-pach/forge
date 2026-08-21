"""Every `uv run X` / `bun run X` a stack README or CLAUDE.md mentions is a declared script."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from forge.registry import ROOT

# (template dir, manifest, the runner prefix its docs use)
STACKS = (
    ("stacks/python/template", "pyproject.toml", "uv run"),
    ("stacks/nextjs/template", "package.json", "bun run"),
)
DOCS = ("README.md", "CLAUDE.md")

# Provided by the runner itself, never declared per project.
BUILTIN = {
    "uv run": {"pytest", "ruff", "mypy", "python", "forge"},
    "bun run": {"dev", "build", "start", "test"},
}


def declared(manifest: Path, kind: str) -> set[str]:
    try:
        if kind == "pyproject.toml":
            data = tomllib.loads(manifest.read_text())
            return set((data.get("project", {}).get("scripts") or {}).keys())
        return set((json.loads(manifest.read_text()).get("scripts") or {}).keys())
    except (OSError, ValueError, tomllib.TOMLDecodeError):
        return set()


def check() -> list[str]:
    errors: list[str] = []
    for base, manifest_name, prefix in STACKS:
        root = ROOT / base
        names = declared(root / manifest_name, manifest_name) | BUILTIN[prefix]
        pattern = re.compile(rf"{re.escape(prefix)}\s+([\w:.-]+)")
        for doc in DOCS:
            path = root / doc
            if not path.is_file():
                continue
            for cmd in sorted(set(pattern.findall(path.read_text()))):
                if cmd not in names:
                    errors.append(
                        f"{base}/{doc} says `{prefix} {cmd}`, "
                        f"which {manifest_name} does not declare"
                    )
        other = "npm run" if prefix == "bun run" else "poetry run"
        if any(other in (root / d).read_text() for d in DOCS if (root / d).is_file()):
            errors.append(f"{base} documents `{other}` but the project uses `{prefix}`")
    return errors
