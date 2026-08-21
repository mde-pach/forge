"""Every declared command resolves to a callable."""

from __future__ import annotations

import importlib


def check() -> list[str]:
    from forge.registry import REGISTRY

    errors: list[str] = []
    for entry in REGISTRY:
        module_name, _, func_name = entry.handler.partition(":")
        if not module_name or not func_name:
            errors.append(f"{entry.name}: handler {entry.handler!r} is not 'module:function'")
            continue
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            errors.append(f"{entry.name}: handler module {module_name!r} does not import ({e})")
            continue
        fn = getattr(module, func_name, None)
        if fn is None:
            errors.append(f"{entry.name}: {module_name!r} has no {func_name!r}")
        elif not callable(fn):
            errors.append(f"{entry.name}: {entry.handler} is not callable")
    return errors
