"""
What forge provides.

One table, read at runtime by the dispatcher. Nothing else enumerates forge's
surface, and nothing forge does is reachable except through here.

Three constraints hold it honest, each added after the previous one turned out
to be satisfiable while still being wrong:

  * `role` is unique. Two entries claiming to serve, or to verify, is a hard
    error at import time.
  * `role` must come from ROLES, a closed vocabulary. Uniqueness alone does not
    bound anything: a seventh command passed the check because a seventh role
    was typed alongside it, for free. Adding a role is now a deliberate edit to
    a list, visible in a diff, in a protected file.
  * A declared command must be invoked by something other than this file - see
    forge.checks.commands. Declaring a command used to make its module reachable
    by definition, so the reachability check could never report one as dead, and
    three of seven had no caller anywhere.

Every field here is read by something. A field nothing reads rots exactly like
prose: a study of configuration systems found only ~28% of declared constraints
were mechanically checkable, and the rest drifted. So there is no `owner`, no
`description`, no `since` - only what the dispatcher, the help text and the
checks consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# The closed vocabulary. A command must fill one of these jobs; there is no
# fourth job. Growing this list is the deliberate act that adding a command
# used to be able to skip.
ROLES: tuple[str, ...] = (
    "session-view",  # look at what my sessions are doing
    "verification",  # is this repo still internally consistent
    "documentation",  # build, verify or preview the docs site
)


@dataclass(frozen=True)
class Entry:
    """One thing forge can do."""

    name: str  # what you type after `forge`
    role: str  # unique, and drawn from ROLES
    summary: str  # one line, shown in `forge --help`
    handler: str  # "module:function", imported on demand
    protected: bool = False  # changing its files requires independent review


REGISTRY: tuple[Entry, ...] = (
    Entry(
        name="start",
        role="session-view",
        summary="Run the session view, reachable from your other devices.",
        handler="forge.commands.start:run",
    ),
    Entry(
        name="check",
        role="verification",
        summary="Every check forge makes about itself. Also run by the Stop hook and CI.",
        handler="forge.commands.check:run",
        protected=True,
    ),
    Entry(
        name="docs",
        role="documentation",
        summary="Build the documentation site, verify it is current, or preview it.",
        handler="forge.commands.docs:run",
    ),
)


def validate() -> None:
    """Enforced at import, so a bad table cannot reach a running system.

    Public because the proofs call it with a deliberately broken table. A check
    whose subject is private is a check you have to reach around to exercise,
    and a check nobody can exercise is not evidence."""
    seen_roles: dict[str, str] = {}
    seen_names: set[str] = set()
    for e in REGISTRY:
        if e.role not in ROLES:
            msg = (
                f"{e.name!r} claims the role {e.role!r}, which is not in ROLES. "
                "Fill an existing role or add one deliberately - a new role is how a "
                "second way to do the same job gets in."
            )
            raise ValueError(msg)
        if e.role in seen_roles:
            msg = (
                f"two entries claim the role {e.role!r}: {seen_roles[e.role]!r} and {e.name!r}. "
                "Exactly one mechanism fills each role - replace the entry, do not add one."
            )
            raise ValueError(msg)
        if e.name in seen_names:
            msg = f"duplicate command name {e.name!r}"
            raise ValueError(msg)
        seen_roles[e.role] = e.name
        seen_names.add(e.name)


validate()


def by_name(name: str) -> Entry | None:
    return next((e for e in REGISTRY if e.name == name), None)


def roles() -> dict[str, str]:
    return {e.role: e.name for e in REGISTRY}
