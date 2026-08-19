"""Validate capability manifests against the contract."""

from __future__ import annotations

import re

import yaml

from forge.registry import ROOT

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
KEBAB = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
REQUIRED = ("name", "version", "need", "triggers", "context", "contract", "verifier")


def check() -> list[str]:
    caps = ROOT / "capabilities"
    errors: list[str] = []
    if not caps.is_dir():
        return ["no capabilities/ directory"]
    for cap in sorted(p for p in caps.iterdir() if p.is_dir() and not p.name.startswith(".")):
        where = f"capabilities/{cap.name}"
        if not (cap / "SKILL.md").is_file():
            errors.append(f"{where}: no SKILL.md")
        path = cap / "manifest.yaml"
        if not path.is_file():
            errors.append(f"{where}: no manifest.yaml")
            continue
        try:
            m = yaml.safe_load(path.read_text())
        except yaml.YAMLError as e:
            errors.append(f"{where}: invalid YAML: {e}")
            continue
        if not isinstance(m, dict):
            errors.append(f"{where}: manifest is not a mapping")
            continue
        errors += [f"{where}: missing {k!r}" for k in REQUIRED if k not in m]
        name = m.get("name")
        if name is not None:
            if not (isinstance(name, str) and KEBAB.match(name)):
                errors.append(f"{where}: name {name!r} is not kebab-case")
            elif name != cap.name:
                errors.append(f"{where}: name {name!r} does not match its directory")
        v = m.get("version")
        if v is not None and not (isinstance(v, str) and SEMVER.match(v)):
            errors.append(f"{where}: version {v!r} is not MAJOR.MINOR.PATCH")
        trig = m.get("triggers")
        if trig is not None and not (isinstance(trig, list) and trig):
            errors.append(f"{where}: triggers must be a non-empty list")
        con = m.get("contract")
        if isinstance(con, dict):
            for k in ("pre", "post"):
                if not (isinstance(con.get(k), list) and con.get(k)):
                    errors.append(f"{where}: contract.{k} must be a non-empty list")
        for a in m.get("assets") or []:
            if not isinstance(a, str) or not (ROOT / a).exists():
                errors.append(f"{where}: assets entry {a!r} does not exist")
    return errors
