"""
What forge provides.

One table, read at runtime by the dispatcher. Nothing else enumerates forge's
surface, and nothing forge does is reachable except through here — so a second
mechanism for the same job has nowhere to plug in, rather than being forbidden
by a rule someone has to remember.

Two constraints hold it honest:

  * `role` is unique. Two entries claiming to install, or to publish, or to
    serve, is a hard error at import time - which is the failure we actually
    had, five times over, for four days.
  * Every field here is read by something. A field nothing reads rots exactly
    like prose: a study of configuration systems found only ~28% of declared
    constraints were mechanically checkable, and the rest drifted. So there is
    no `owner`, no `description`, no `since` - only what the dispatcher, the
    help text and the checks consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class Entry:
    """One thing forge can do."""

    name: str  # what you type after `forge`
    role: str  # unique; what job this fills
    summary: str  # one line, shown in `forge --help`
    handler: str  # "module:function", imported on demand
    protected: bool = False  # changing its files requires independent review


REGISTRY: tuple[Entry, ...] = (
    Entry(
        name="scaffold",
        role="project-creation",
        summary="Create a project with its quality gates already wired.",
        handler="forge.commands.scaffold:run",
    ),
    Entry(
        name="serve",
        role="session-view",
        summary="Serve the session view on localhost.",
        handler="forge.commands.serve:run",
    ),
    Entry(
        name="expose",
        role="session-view-reach",
        summary="Reach the session view from your other devices, over Tailscale.",
        handler="forge.commands.expose:run",
    ),
    Entry(
        name="doctor",
        role="diagnosis",
        summary="Report what is working, and which step failed if something is not.",
        handler="forge.commands.doctor:run",
    ),
    Entry(
        name="check",
        role="verification",
        summary="Run every check forge makes about itself.",
        handler="forge.commands.check:run",
        protected=True,
    ),
    Entry(
        name="parity",
        role="mirror-parity",
        summary="Check the remote holds exactly what this checkout holds.",
        handler="forge.commands.parity:run",
    ),
    Entry(
        name="docs",
        role="documentation",
        summary="Regenerate generated documentation, or verify it is current.",
        handler="forge.commands.docs:run",
    ),
)


def _validate() -> None:
    """Enforced at import, so a duplicate role cannot reach a running system."""
    seen_roles: dict[str, str] = {}
    seen_names: set[str] = set()
    for e in REGISTRY:
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


_validate()


def by_name(name: str) -> Entry | None:
    return next((e for e in REGISTRY if e.name == name), None)


def roles() -> dict[str, str]:
    return {e.role: e.name for e in REGISTRY}
