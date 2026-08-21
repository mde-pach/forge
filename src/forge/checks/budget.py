"""Every tracked code and markdown file is within the prose budget the admission hook enforces."""

from __future__ import annotations

import importlib.util
from types import ModuleType

from forge.checks.orphans import repo_files
from forge.registry import ROOT

ADMIT = ROOT / "plugins" / "forge-guard" / "hooks" / "admit.py"
SKIP = ("stacks/", ".claude/reviews/")


def _admit() -> ModuleType:
    spec = importlib.util.spec_from_file_location("admit", ADMIT)
    if spec is None or spec.loader is None:
        msg = f"cannot load {ADMIT}"
        raise ImportError(msg)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check() -> list[str]:
    admit = _admit()
    errs = []
    for f in repo_files():
        if f.startswith(SKIP):
            continue
        try:
            src = (ROOT / f).read_text()
        except (OSError, UnicodeDecodeError):
            continue
        m = admit.measure(f, src)
        if m is None:
            continue
        bad = admit.violations(m)
        if bad:
            errs.append(f"{f}: {', '.join(bad)}")
    return errs
