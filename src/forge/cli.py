"""
The one way to run anything forge does.

Invoking a file by path is what let five install mechanisms coexist: each one
worked on its own and nothing enumerated them. Here, a command that is not in
the registry is not reachable, and `forge --help` is generated from the same
table the dispatcher resolves against, so the help cannot describe something
that does not run.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Sequence

from forge.registry import REGISTRY, by_name


def _usage() -> str:
    width = max(len(e.name) for e in REGISTRY)
    lines = ["usage: forge <command> [args...]", "", "commands:"]
    lines += [f"  {e.name:<{width}}  {e.summary}" for e in sorted(REGISTRY, key=lambda e: e.name)]
    lines += ["", "Every command is declared in forge.registry; nothing else is reachable."]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help", "help"):
        print(_usage())
        return 0

    name, rest = args[0], args[1:]
    entry = by_name(name)
    if entry is None:
        print(f"forge: no command named {name!r}\n", file=sys.stderr)
        print(_usage(), file=sys.stderr)
        return 2

    module_name, _, func_name = entry.handler.partition(":")
    module = importlib.import_module(module_name)
    handler = getattr(module, func_name)
    return int(handler(rest) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
