"""Every file is reachable from something that runs; prose-only reach is reported separately.

Tests, verifiers and checkers do not propagate liveness, so a checker must not
spell out the path it looks for.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path

from forge.registry import ROOT

EXEC_ROOTS = (
    "pyproject.toml",
    "package.json",
    ".github/workflows/*.yml",
    ".github/dependabot.yml",
    ".claude-plugin/marketplace.json",
    ".claude/settings.json",
    "src/forge/*.py",
    "src/forge/commands/*.py",
    "plugins/*/.claude-plugin/plugin.json",
    "plugins/*/hooks/hooks.json",
    "docs/.vitepress/config.mjs",
    "docs/.vitepress/assemble.mjs",
)

DOC_ROOTS = ("README.md", "docs/*.md", "docs/*/*.md", "plugins/*/README.md")

NON_PROPAGATING_EXEC = (
    "plugins/*/verify.sh",
    "src/forge/checks/*.py",
    "*/tests/*",
    "tests/*",
    "*.md",
)
NON_PROPAGATING_DOC = ("plugins/*/verify.sh", "src/forge/checks/*.py")

# Found by a tool by name.
CONVENTIONAL = re.compile(
    r"(^|/)("
    r"SKILL\.md|manifest\.yaml|plugin\.json|marketplace\.json|hooks\.json|settings\.json"
    r"|__init__\.py|\.gitkeep|\.gitignore|\.nvmrc|CLAUDE\.md|README\.md"
    r"|LICENSE|dependabot\.yml|package-lock\.json|uv\.lock|index\.md|conftest\.py|test_[\w]+\.py"
    r")$"
)

# Copied into generated projects.
EXEMPT_PREFIX = ("stacks/", "contract/template/")

REFERENCE_GLOB = ".claude/skills/*/references/*"

# Contents are found by directory or derived name, never by a written path.
SERVED_DIRS = (
    "plugins/forge-monitor/dashboard/",
    "plugins/forge-monitor/fixtures/",
    ".claude/reviews/",
)

# Checked by forge.checks.commands instead.
COMMAND_MODULES = "src/forge/commands/*.py"


def repo_files() -> list[str]:

    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted({line for line in out.stdout.splitlines() if line})


def _match(files: list[str], patterns: tuple[str, ...]) -> set[str]:
    return {f for f in files for p in patterns if f == p or fnmatch.fnmatch(f, p)}


def _tokens(text: str) -> tuple[set[str], set[str], set[str]]:

    paths = set(re.findall(r"/?[\w.@-]+(?:/[\w.@-]+)+", text))
    paths |= set(re.findall(r"/[\w.@-]+", text))
    names = set(re.findall(r"[\w.@-]+\.[A-Za-z0-9]{1,8}\b", text))
    imports = set(re.findall(r"(?:^|\b)(?:import|from)\s+([\w.]+)", text, re.MULTILINE))
    return paths, names, imports


def _links(f: str, paths: set[str], names: set[str], imports: set[str]) -> bool:
    path = Path(f)
    if f in paths or any(p.endswith("/" + f) or f.endswith("/" + p) for p in paths):
        return True
    if path.name in names:
        return True
    if path.suffix == ".py" and (
        path.stem in imports or any(i.split(".")[-1] == path.stem for i in imports)
    ):
        return True
    if path.suffix == ".md":  # VitePress links without the extension
        stem_path = str(path.with_suffix("")).removeprefix("docs/")
        if any(p.lstrip("/").endswith(stem_path) for p in paths):
            return True
    return False


def _reachable(files: list[str], seeds: set[str], blocked: tuple[str, ...]) -> set[str]:
    live = set(seeds)
    frontier = list(live)
    while frontier:
        current = frontier.pop()
        if any(fnmatch.fnmatch(current, p) for p in blocked):
            continue
        path = ROOT / current
        if not path.is_file():
            continue
        try:
            paths, names, imports = _tokens(path.read_text(errors="replace"))
        except OSError:
            continue
        for f in files:
            if f not in live and _links(f, paths, names, imports):
                live.add(f)
                frontier.append(f)
    return live


def find(files: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Returns (orphans, described_but_unused)."""
    files = files or repo_files()
    exec_live = _reachable(files, _match(files, EXEC_ROOTS), NON_PROPAGATING_EXEC)
    doc_live = _reachable(files, _match(files, DOC_ROOTS), NON_PROPAGATING_DOC)

    def ignorable(f: str) -> bool:
        return (
            bool(CONVENTIONAL.search(f))
            or f.startswith(EXEMPT_PREFIX)
            or f.startswith(SERVED_DIRS)
            or fnmatch.fnmatch(f, COMMAND_MODULES)
        )

    orphans = sorted(f for f in files if f not in exec_live | doc_live and not ignorable(f))
    described_only = sorted(
        f
        for f in files
        if f in doc_live
        and f not in exec_live
        and not ignorable(f)
        and not fnmatch.fnmatch(f, REFERENCE_GLOB)
    )
    return orphans, described_only


def uncited_references(files: list[str] | None = None) -> list[str]:
    """Capability references not cited by their own SKILL.md."""
    files = files or repo_files()
    out = []
    for f in files:
        if not fnmatch.fnmatch(f, REFERENCE_GLOB):
            continue
        skill = ROOT / Path(f).parent.parent / "SKILL.md"
        if not skill.is_file() or Path(f).name not in skill.read_text(errors="replace"):
            out.append(f)
    return sorted(out)
