"""
A declared command that nothing invokes.

This exists because of a specific failure: `forge check` printed
`ok  7 commands, 7 distinct roles` while three of those seven - `expose`,
`doctor`, `docs` - had no caller anywhere in the repository. Cardinality was
the wrong property. The registry counted; it did not ask whether anything
reached what it counted.

And reachability could not ask either, because `src/forge/commands/*.py` was a
liveness root in the orphan checker: declaring a command was what made its
module live. A registry that confers liveness on its own entries can never
report one as dead. So command modules are now exempt from the orphan checker
entirely and this check owns them instead - one property, one owner.

The honest limit: `parity` WAS invoked, by CI, and would have passed this. It
was a bad idea rather than dead code, and no mechanical check catches a bad
idea. This catches the cheaper failure - the thing nobody ever wired up - which
is two of the three.

`FRICTIONS.md` is deliberately not a caller. A post-mortem that mentions a
command is describing it, not running it, and treating prose as evidence of
liveness is the exact mistake the orphan checker was built to stop making.
"""

from __future__ import annotations

import fnmatch
import re

from forge import registry
from forge.checks.orphans import repo_files
from forge.registry import ROOT

# Files whose contents count as invoking a command: things that run, plus the
# two documents that tell a human what to type.
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


# The one spelling. `uv run forge <cmd>` is what the README documents, what the
# Stop hook runs and what CI runs, so it is also the only thing recognised here.
# An earlier version accepted a bare `forge <cmd>`, which matched English -
# "forge provides", "forge maintains" - and reported twelve sentences as broken
# invocations. Requiring the runner is both precise and the property worth
# enforcing: a second accepted spelling is a second way in.
PREFIX = r"\buv\s+run\s+forge\s+"
INVOKE = re.compile(PREFIX + r"(?P<cmd>[\w-]+)")


def _callers(name: str, files: list[str]) -> list[str]:
    """Where `name` is invoked from. All three spellings the repo actually uses."""
    # Built from the same PREFIX as INVOKE rather than by editing INVOKE's
    # pattern text. The string-surgery version silently failed to substitute -
    # so every command matched every invocation and the check reported all
    # clear. Its proof caught it; nothing else would have.
    pattern = re.compile(PREFIX + re.escape(name) + r"\b")
    out = []
    for f in files:
        if not any(fnmatch.fnmatch(f, p) for p in CALLER_ROOTS):
            continue
        try:
            if pattern.search((ROOT / f).read_text(errors="replace")):
                out.append(f)
        except OSError:
            continue
    return out


def call_sites() -> dict[str, list[str]]:
    files = repo_files()
    # `registry.REGISTRY`, not a name imported at module load: the proof that
    # this check works substitutes the table, and a bound name would keep
    # pointing at the original - so the check silently examined a registry that
    # did not contain the planted command and reported all clear.
    return {e.name: _callers(e.name, files) for e in registry.REGISTRY}


def undeclared() -> list[str]:
    """The inverse question: a document or workflow telling you to run a command
    that does not exist. Deleting `forge scaffold` left two how-to pages and a
    SKILL.md still instructing you to type it - a mechanism removed cleanly and
    still described everywhere, which is the same defect as the reverse."""
    known = {e.name for e in registry.REGISTRY}
    files = repo_files()
    out = []
    for f in files:
        if not any(fnmatch.fnmatch(f, p) for p in CALLER_ROOTS):
            continue
        try:
            text = (ROOT / f).read_text(errors="replace")
        except OSError:
            continue
        for word in {m.group("cmd") for m in INVOKE.finditer(text)}:
            if word in known or word.startswith("-"):  # `forge --help` is a flag
                continue
            out.append(f"{f} tells you to run `forge {word}`, which is not a declared command")
    return sorted(out)


def check() -> list[str]:
    return [
        f"`forge {name}` is declared but nothing invokes it - "
        f"delete it, or wire it into a workflow, a hook or a how-to"
        for name, sites in call_sites().items()
        if not sites
    ] + undeclared()
