#!/usr/bin/env python3
"""Validate every capability manifest against contract/CONTRACT.md v1.0.0.

The previous check only asked whether a handful of keys were present, and it
iterated over the manifests it found -- so a capability with NO manifest was
invisible to it. This one starts from the capability directories, so a missing
manifest is a failure, and it checks shapes rather than presence.

Exit 0 = every capability is valid. Exit 1 = at least one is not.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("validate-manifests: pyyaml required (pip install pyyaml --break-system-packages)")

ROOT = Path(__file__).resolve().parent.parent
CAPS = ROOT / "capabilities"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

REQUIRED = ("name", "version", "need", "triggers", "context", "contract", "verifier")

errors: list[str] = []


def err(where: str, msg: str) -> None:
    errors.append(f"{where}: {msg}")


def check(cap_dir: Path) -> None:
    name = cap_dir.name
    where = f"capabilities/{name}"

    skill = cap_dir / "SKILL.md"
    if not skill.is_file():
        err(where, "no SKILL.md - the projection would ship an empty skill")

    path = cap_dir / "manifest.yaml"
    if not path.is_file():
        err(where, "no manifest.yaml (the contract requires one per capability)")
        return

    try:
        m = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        err(where, f"invalid YAML: {e}")
        return
    if not isinstance(m, dict):
        err(where, "manifest is not a mapping")
        return

    for key in REQUIRED:
        if key not in m:
            err(where, f"missing required key `{key}`")

    if "name" in m:
        if not isinstance(m["name"], str) or not KEBAB.match(m["name"]):
            err(where, f"name `{m['name']!r}` is not kebab-case")
        elif m["name"] != name:
            err(where, f"name `{m['name']}` does not match its directory `{name}`")

    if "version" in m and not (isinstance(m["version"], str) and SEMVER.match(m["version"])):
        err(where, f"version `{m['version']!r}` is not MAJOR.MINOR.PATCH")

    if "need" in m and not (isinstance(m["need"], str) and m["need"].strip()):
        err(where, "need is empty - a capability with no stated need should not exist")

    trig = m.get("triggers")
    if trig is not None and not (isinstance(trig, list) and trig):
        err(where, "triggers must be a non-empty list (when does this capability fire?)")

    ctx = m.get("context")
    if ctx is not None:
        if not isinstance(ctx, dict):
            err(where, "context must be a mapping with `loads` and `never`")
        else:
            for k in ("loads", "never"):
                if k not in ctx:
                    err(where, f"context.{k} is missing - context discipline is declared, not assumed")

    con = m.get("contract")
    if con is not None:
        if not isinstance(con, dict):
            err(where, "contract must be a mapping")
        else:
            for k in ("pre", "post"):
                v = con.get(k)
                if not (isinstance(v, list) and v):
                    err(where, f"contract.{k} must be a non-empty list")

    assets = m.get("assets")
    if assets is not None:
        if not isinstance(assets, list) or not assets:
            err(where, "assets must be a non-empty list of repo-relative paths")
        else:
            for a in assets:
                if not isinstance(a, str) or not (ROOT / a).exists():
                    err(where, f"assets entry `{a!r}` does not exist in the repo")

    ver = m.get("verifier")
    if ver is not None and not (isinstance(ver, (str, dict)) and ver):
        err(where, "verifier is empty - kernel 6 requires a separated check")


def main() -> int:
    if not CAPS.is_dir():
        print("validate-manifests: no capabilities/ directory", file=sys.stderr)
        return 1
    caps = sorted(p for p in CAPS.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not caps:
        print("validate-manifests: no capabilities found", file=sys.stderr)
        return 1
    for cap in caps:
        check(cap)

    if errors:
        print(f"validate-manifests: {len(errors)} problem(s) across {len(caps)} capabilities:\n", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"validate-manifests: {len(caps)} capabilities valid ({', '.join(c.name for c in caps)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
