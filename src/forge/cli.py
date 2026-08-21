"""Dispatcher: `forge <command>` resolves against the registry and nothing else."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Sequence

from forge.registry import REGISTRY, by_name


def _usage() -> str:
    width = max(len(e.name) for e in REGISTRY)
    lines = ["usage: forge <command> [args...]", "", "commands:"]
    lines += [f"  {e.name:<{width}}  {e.summary}" for e in sorted(REGISTRY, key=lambda e: e.name)]
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
    handler = getattr(importlib.import_module(module_name), func_name)
    return int(handler(rest) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
