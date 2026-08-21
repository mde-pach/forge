"""Every declared command is invoked somewhere, and every invoked command is declared.

Only `uv run forge <cmd>` counts as an invocation: it is the spelling the
README, the Stop hook and CI use. Prose does not count as a caller.
"""

from __future__ import annotations

import fnmatch
import re

from forge import registry
from forge.checks.orphans import repo_files
from forge.registry import ROOT

CALLER_ROOTS = (
    ".github/workflows/*.yml",
    ".claude/hooks/*.sh",
    "plugins/*/hooks/*.json",
    "plugins/*/hooks/*.py",
    "plugins/*/hooks/*.sh",
    ".claude/skills/*/SKILL.md",
    ".claude/skills/*/*.sh",
    "package.json",
    "README.md",
    "docs/how-to/*.md",
)

PREFIX = r"\buv\s+run\s+forge\s+"
INVOKE = re.compile(PREFIX + r"(?P<cmd>[\w-]+)")


def _caller_texts(files: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for f in files:
        if not any(fnmatch.fnmatch(f, p) for p in CALLER_ROOTS):
            continue
        try:
            out[f] = (ROOT / f).read_text(errors="replace")
        except OSError:
            continue
    return out


def call_sites() -> dict[str, list[str]]:
    texts = _caller_texts(repo_files())
    # `registry.REGISTRY` is looked up at call time so tests can substitute the table.
    return {
        e.name: [f for f, t in texts.items() if re.search(PREFIX + re.escape(e.name) + r"\b", t)]
        for e in registry.REGISTRY
    }


def undeclared() -> list[str]:
    known = {e.name for e in registry.REGISTRY}
    out = []
    for f, text in _caller_texts(repo_files()).items():
        for word in {m.group("cmd") for m in INVOKE.finditer(text)}:
            if word not in known and not word.startswith("-"):
                out.append(f"{f} tells you to run `forge {word}`, which is not a declared command")
    return sorted(out)


def check() -> list[str]:
    return [
        f"`forge {name}` is declared but nothing invokes it"
        for name, sites in call_sites().items()
        if not sites
    ] + undeclared()
