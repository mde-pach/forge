"""What forge provides; read by the dispatcher, `--help` and the checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# One command per role; adding a role is a deliberate edit here.
ROLES: tuple[str, ...] = (
    "session-view",
    "verification",
    "documentation",
)


@dataclass(frozen=True)
class Entry:
    name: str
    role: str  # one of ROLES, unique
    summary: str  # shown in `forge --help`
    handler: str  # "module:function"
    protected: bool = False


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

    seen_roles: dict[str, str] = {}
    seen_names: set[str] = set()
    for e in REGISTRY:
        if e.role not in ROLES:
            msg = f"{e.name!r} claims the role {e.role!r}, which is not in ROLES"
            raise ValueError(msg)
        if e.role in seen_roles:
            msg = f"two entries claim the role {e.role!r}: {seen_roles[e.role]!r} and {e.name!r}"
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
