"""
Find files nothing runs, and files only documentation keeps alive.

The first version of this check reported five orphans, four of which were its
own regex failing, and missed the one file that actually was dead. `statusline.sh`
looked live because the README mentions it - so "someone wrote about it" counted
as "something uses it".

That is the wrong model, and fixing it produced the useful distinction:

  * reachable from code, config or CI  -> live
  * reachable only from prose or tests -> DESCRIBED BUT UNUSED
  * reachable from neither             -> orphan

Tests are deliberately not roots. A file is live because something does its job
with it, not because something asserts things about it - otherwise a check
keeps its own subject alive, which is how `statusline.sh` survived: nothing used
it, but the verifier exercised it, so every reachability argument said "live".

The middle category is the interesting one. It is exactly the shape of a
mechanism that was replaced, left on disk, and still described in a document -
which is the failure this whole exercise exists to prevent.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path

from forge.registry import ROOT

# Things that run: entry points, manifests, workflows, config.
EXEC_ROOTS = (
    "pyproject.toml",
    "package.json",
    ".github/workflows/*.yml",
    ".github/dependabot.yml",
    ".claude-plugin/marketplace.json",
    ".claude/settings.json",
    # Enumerated, not globbed: `src/forge/**/*.py` also matched the checks
    # themselves, so this file's own docstring - which names statusline.sh as an
    # example of dead code - made statusline.sh reachable. A checker must not be
    # a liveness root for what it describes.
    #
    # Command modules are roots so that what they use stays live - drop them and
    # serve.py, paths.py and the dashboard all go dark. But being a root is why
    # a dead command was invisible: declaring it made it live BY DEFINITION, and
    # three of seven had no caller while this check reported everything
    # reachable. So they are roots here and unreportable here (COMMAND_MODULES,
    # below); whether anything actually invokes one is a stricter question,
    # asked by forge.checks.commands. One property, one owner.
    "src/forge/*.py",
    "src/forge/commands/*.py",
    "plugins/*/.claude-plugin/plugin.json",
    "plugins/*/hooks/hooks.json",
    "docs/.vitepress/config.mjs",
    "docs/.vitepress/assemble.mjs",
)

# Things that describe or assert.
DOC_ROOTS = ("README.md", "FRICTIONS.md", "docs/*.md", "docs/*/*.md", "plugins/*/README.md")

# Files that never pass liveness on, even when something runs them. A test is a
# consumer, not a producer: CI running the verifier makes the VERIFIER live, it
# does not make everything the verifier touches live. Without this, any check
# keeps its own subject alive and reachability can never find dead code.
NON_PROPAGATING_EXEC = (
    "plugins/*/verify.sh",
    "src/forge/checks/*.py",
    "*/tests/*",
    "tests/*",
    "*.md",  # prose reached from code still does not make code live
)
NON_PROPAGATING_DOC = ("plugins/*/verify.sh", "src/forge/checks/*.py")

# Files a tool finds by name, whose presence is their contract.
CONVENTIONAL = re.compile(
    r"(^|/)("
    r"SKILL\.md|manifest\.yaml|plugin\.json|marketplace\.json|hooks\.json|settings\.json"
    r"|__init__\.py|\.gitkeep|\.gitignore|\.nvmrc|CLAUDE\.md|FRICTIONS\.md|README\.md"
    r"|LICENSE|dependabot\.yml|package-lock\.json|uv\.lock|index\.md"
    r")$"
)

# Copied wholesale into generated projects; their internal wiring is the
# generated project's concern, and each ships its own checks.
EXEMPT_PREFIX = ("stacks/", "contract/template/")

# Capability reference files are prose BY DESIGN - the contract says they load
# only when a SKILL.md points at one. So "prose-only" is correct for them, and
# the real question is a different one, checked separately below: is each
# actually cited by its own SKILL.md, or orphaned from the thing that needs it?
REFERENCE_GLOB = ".claude/skills/*/references/*"

# Directories whose contents are found programmatically rather than named in
# prose or code, so nothing could reference an individual file's path even in
# principle: dashboard/ is served as a whole by serve.py, and .claude/reviews/
# is looked up by recomputing a content-hash fingerprint of the reviewed files
# (plugins/forge-guard/hooks/protected.py) - the filename is derived, never
# written down anywhere else - and fixtures/ is found by assembling
# events-<EventName>.json from the event under test (verify.sh 11), so no
# fixture's path is ever spelled out either.
SERVED_DIRS = (
    "plugins/forge-monitor/dashboard/",
    "plugins/forge-monitor/fixtures/",
    ".claude/reviews/",
)

# Owned by forge.checks.commands, which asks a stricter question than this file
# can: not "does any text mention it" but "does anything actually invoke it".
# Reported here as well, they would be false positives; reported here INSTEAD,
# they were invisible.
COMMAND_MODULES = "src/forge/commands/*.py"


def repo_files() -> list[str]:
    """Every file git considers part of the repo, INCLUDING ones not yet added.

    This was `git ls-files`, which lists only tracked files - so a brand-new
    file was invisible to every check built on it until someone staged it. That
    is precisely backwards: a file written thirty seconds ago is where a new
    defect lives, and the Stop hook that runs these checks fires while it is
    still untracked. It cost a red build to notice: the friction checker's own
    docstring contained a dangling citation, its own check could not see the
    file, and CI - which reads a fresh clone where everything is tracked - could.

    `--exclude-standard` keeps .gitignore honoured, so build artifacts stay out.
    A scratch file that is neither ignored nor used is not a false positive; it
    is the thing being looked for.
    """
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted({line for line in out.stdout.splitlines() if line})


def _match(files: list[str], patterns: tuple[str, ...]) -> set[str]:
    """fnmatch against the full path, not Path.match, which is suffix-based and
    silently matched `stacks/*/template/.github/workflows/ci.yml` as if it were
    this repo's own workflow."""
    return {f for f in files for p in patterns if f == p or fnmatch.fnmatch(f, p)}


def _tokens(text: str) -> tuple[set[str], set[str], set[str]]:
    """Three kinds of reference, kept apart because they have different rules.

    Loose matching is what made an earlier version useless: matching any file
    whose bare name appeared anywhere linked `config.mjs` to `CLAUDE.md` to
    `settings.json`, and the whole repo became one connected blob in which
    nothing could ever be dead.
    """
    paths = set(re.findall(r"/?[\w.@-]+(?:/[\w.@-]+)+", text))  # a/b/c.ext, /a/b
    paths |= set(re.findall(r"/[\w.@-]+", text))  # /single-segment link
    names = set(re.findall(r"[\w.@-]+\.[A-Za-z0-9]{1,8}\b", text))  # c.ext
    imports = set(re.findall(r"(?:^|\b)(?:import|from)\s+([\w.]+)", text, re.MULTILINE))
    return paths, names, imports


def _links(f: str, paths: set[str], names: set[str], imports: set[str]) -> bool:
    """Does any reference in a file point at `f`? Precise on purpose."""
    path = Path(f)
    if f in paths or any(p.endswith("/" + f) or f.endswith("/" + p) for p in paths):
        return True
    if path.name in names:
        return True
    if path.suffix == ".py" and (
        path.stem in imports or any(i.split(".")[-1] == path.stem for i in imports)
    ):
        return True
    # VitePress and similar link without the extension: /how-to/monitor
    if path.suffix == ".md":
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
    """A capability reference not cited by its own SKILL.md.

    The contract says a reference is 'loaded only when SKILL.md points to it',
    so one that nothing points to is shipped in every projection and read by
    nobody - and the capability that depends on it never gets it.
    """
    files = files or repo_files()
    out = []
    for f in files:
        if not fnmatch.fnmatch(f, REFERENCE_GLOB):
            continue
        skill = ROOT / Path(f).parent.parent / "SKILL.md"
        if not skill.is_file():
            out.append(f)
            continue
        if Path(f).name not in skill.read_text(errors="replace"):
            out.append(f)
    return sorted(out)
