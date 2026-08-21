"""Prose density of the tree, as a gauge: printed, never failed on."""

from __future__ import annotations

import importlib.util
import statistics
from types import ModuleType

from forge.checks.orphans import repo_files
from forge.registry import ROOT

ADMIT = ROOT / "plugins" / "forge-guard" / "hooks" / "admit.py"


def _admit() -> ModuleType:
    spec = importlib.util.spec_from_file_location("admit", ADMIT)
    if spec is None or spec.loader is None:
        msg = f"cannot load {ADMIT}"
        raise ImportError(msg)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _current(admit: ModuleType, kind: str) -> dict[str, float]:
    out = {}
    for f in repo_files():
        if admit.KINDS.get(f[f.rfind(".") :]) != kind:
            continue
        try:
            d = admit.density(f, (ROOT / f).read_text())
        except (OSError, UnicodeDecodeError):
            continue
        if d is not None:
            out[f] = d
    return out


def gauge() -> list[str]:
    admit = _admit()
    lines = []
    for kind, label in (("py", "python  "), ("sh", "shell   "), ("md", "markdown")):
        now = _current(admit, kind)
        head = admit.tree_densities(ROOT, kind)
        if not now:
            continue
        med = statistics.median(now.values())
        ref = statistics.median(head.values()) if head else med
        lines.append(f"  {label}  median {med:.2f}  (HEAD {ref:.2f})")
    densest = sorted(_current(admit, "py").items(), key=lambda kv: -kv[1])[:3]
    for f, d in densest:
        lines.append(f"  densest   {f} {d:.2f}")
    return lines
