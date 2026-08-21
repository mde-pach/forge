"""Each check is shown to fail on the defect it exists for."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import forge.registry as reg
from forge.checks import commands, documented_commands, handlers, orphans
from forge.checks import hook_parity as hp
from forge.registry import ROLES, ROOT, Entry

Wiring = tuple[dict[str, Any], dict[str, Any]]
Registry = Callable[[Entry], None]

# Names below are assembled, not written literally: a literal path in a test
# would make the planted file reachable and the test would stop testing.
PLANTED = "plugins/forge-monitor/__planted" + "_orphan.sh"


@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch) -> Registry:
    def with_entry(entry: Entry) -> None:
        monkeypatch.setattr(reg, "REGISTRY", (*reg.REGISTRY, entry))

    return with_entry


# --- reachability -----------------------------------------------------------


def test_orphan_is_reported() -> None:
    found, _ = orphans.find([*orphans.repo_files(), PLANTED])
    assert PLANTED in found


@pytest.mark.parametrize(
    "path",
    [
        ".claude/reviews/__planted" + ".md",
        "plugins/forge-monitor/fixtures/events-__Planted" + ".json",
    ],
)
def test_derived_name_dirs_are_exempt(path: str) -> None:
    found, _ = orphans.find([*orphans.repo_files(), path])
    assert path not in found


def test_unstaged_files_are_listed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "new.md").write_text("x\n")
    monkeypatch.setattr(orphans, "ROOT", tmp_path)
    assert "new.md" in orphans.repo_files()


# --- hook parity ------------------------------------------------------------


@pytest.fixture
def wiring() -> Wiring:
    settings = json.loads((ROOT / hp.SETTINGS).read_text())
    manifest = json.loads((ROOT / hp.MONITOR_MANIFEST).read_text())
    return settings, manifest


def test_clean_wiring_passes(wiring: Wiring) -> None:
    assert hp.check(*wiring) == []


def test_manifest_event_missing_from_settings(wiring: Wiring) -> None:
    settings, manifest = wiring
    grown = copy.deepcopy(manifest)
    grown["hooks"]["__PlantedEvent"] = [
        {"hooks": [{"type": "command", "command": "sh", "args": ["x"]}]}
    ]
    assert any("__PlantedEvent" in e for e in hp.check(settings, grown))


def test_settings_event_missing_from_manifest(wiring: Wiring) -> None:
    settings, manifest = wiring
    shrunk = copy.deepcopy(manifest)
    del shrunk["hooks"]["PreCompact"]
    assert any("does not declare" in e for e in hp.check(settings, shrunk))


def test_monitor_timeout_drift(wiring: Wiring) -> None:
    settings, manifest = wiring
    drifted = copy.deepcopy(settings)
    for _ev, h in hp._flat(drifted["hooks"]):
        if h.get("args") == [hp.EMIT, "SessionEnd"]:
            h["timeout"] = 1
    assert any("SessionEnd" in e and "timeout" in e for e in hp.check(drifted, manifest))


def test_duplicated_monitor_entry(wiring: Wiring) -> None:
    settings, manifest = wiring
    doubled = copy.deepcopy(settings)
    doubled["hooks"]["SessionEnd"].append(copy.deepcopy(doubled["hooks"]["SessionEnd"][0]))
    assert any("fires 2 times" in e for e in hp.check(doubled, manifest))


def test_guard_unpinned(wiring: Wiring) -> None:
    settings, manifest = wiring
    unpinned = copy.deepcopy(settings)
    for _ev, h in hp._flat(unpinned["hooks"]):
        h["args"] = [str(a).replace("origin/main:", "") for a in h.get("args") or []]
    assert any("pinned" in e for e in hp.check(unpinned, manifest))


def test_guard_async(wiring: Wiring) -> None:
    settings, manifest = wiring
    softened = copy.deepcopy(settings)
    for ev, h in hp._flat(softened["hooks"]):
        if ev == "Stop" and (h.get("args") or [None])[0] == "-c":
            h["async"] = True
    assert any("async guard" in e for e in hp.check(softened, manifest))


def test_guard_timeout_drift(wiring: Wiring) -> None:
    settings, manifest = wiring
    slow = copy.deepcopy(settings)
    for ev, h in hp._flat(slow["hooks"]):
        if ev == "UserPromptSubmit" and (h.get("args") or [None])[0] == "-c":
            h["timeout"] = 999
    assert any("UserPromptSubmit" in e and "timeout" in e for e in hp.check(slow, manifest))


def test_guard_on_undeclared_event(wiring: Wiring) -> None:
    settings, manifest = wiring
    ghost = copy.deepcopy(settings)
    ghost["hooks"]["SessionEnd"].append(copy.deepcopy(ghost["hooks"]["Stop"][0]))
    assert any("does not declare" in e and "guard" in e for e in hp.check(ghost, manifest))


def test_marketplace_plugin_reenabled(wiring: Wiring) -> None:
    settings, manifest = wiring
    reenabled = copy.deepcopy(settings)
    reenabled["enabledPlugins"]["forge-guard@forge"] = True
    assert any("both copies would fire" in e for e in hp.check(reenabled, manifest))


def test_pinned_copy_differs_from_tree() -> None:
    assert any(
        "differs from the tree copy" in e for e in hp.drift(reader=lambda _p: b"__tampered__")
    )


# --- registry ---------------------------------------------------------------


def test_registry_rejects_duplicate_role(registry: Registry) -> None:
    registry(Entry("dup", reg.REGISTRY[0].role, "x", "x:y"))
    with pytest.raises(ValueError, match="two entries claim"):
        reg.validate()


def test_registry_rejects_unknown_role(registry: Registry) -> None:
    registry(Entry("invented", "a-brand-new-job", "x", "x:y"))
    with pytest.raises(ValueError, match="not in ROLES"):
        reg.validate()


def test_missing_handler_is_caught(registry: Registry) -> None:
    registry(Entry("ghost", ROLES[0], "x", "forge.commands.nothing:run"))
    assert any("does not import" in e for e in handlers.check())


def test_uncalled_command_is_caught(registry: Registry) -> None:
    registry(Entry("__uncalled", ROLES[0], "x", "forge.commands.check:run"))
    assert any("__uncalled" in e for e in commands.check())


# --- documented commands ----------------------------------------------------


def test_undeclared_documented_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tpl = "stacks/nextjs/template"
    (tmp_path / tpl).mkdir(parents=True)
    for name in ("package.json", "README.md"):
        shutil.copy(ROOT / tpl / name, tmp_path / tpl / name)
    (tmp_path / tpl / "README.md").open("a").write("\nbun run __not_a_real_script\n")
    monkeypatch.setattr(documented_commands, "ROOT", tmp_path)
    assert any("__not_a_real_script" in e for e in documented_commands.check())
