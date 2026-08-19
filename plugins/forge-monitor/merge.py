#!/usr/bin/env python3
"""
Merge every machine's snapshot into one view.

This exists because the dashboard was reading local state directly, which made
it structurally single-machine: `claude agents` spans one machine, and one
machine's event log is on that machine's disk. The store is the only place the
machines meet, so the store — not the laptop — is the source of truth.

    python3 merge.py <store-dir>     # reads <store>/sessions/*/snapshot.json
                                     # writes <store>/snapshot.json + STATUS.md
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def merge(store: Path) -> dict:
    waiting: list[dict] = []
    active: list[dict] = []
    recent: list[dict] = []
    machines: dict[str, str] = {}

    for snap_path in sorted((store / "sessions").glob("*/snapshot.json")):
        host = snap_path.parent.name
        try:
            snap = json.loads(snap_path.read_text())
        except (OSError, ValueError):
            continue
        machines[host] = snap.get("generated_at") or "?"
        for bucket, dest in (("waiting", waiting), ("active", active), ("recent", recent)):
            for s in snap.get(bucket, []):
                s.setdefault("host", host)
                dest.append(s)

    key = lambda s: s.get("attention_since") or s.get("last_seen") or ""  # noqa: E731
    waiting.sort(key=key)                 # oldest demand first: it has waited longest
    active.sort(key=key, reverse=True)
    recent.sort(key=key, reverse=True)
    recent = recent[:15]

    return {
        "generated_at": now(),
        "machines": machines,
        "counts": {"waiting": len(waiting), "active": len(active), "recent": len(recent)},
        "waiting": waiting, "active": active, "recent": recent,
    }


def status_md(m: dict) -> str:
    def row(s: dict) -> str:
        return (f"| `{s.get('project', '?')}` | {s.get('state', '?')} | "
                f"{s.get('attention_reason') or '—'} | {s.get('host', '?')} | "
                f"{s.get('last_seen', '?')} | `{str(s.get('session_id', ''))[:8]}` |")

    hdr = "| project | state | why | machine | since | id |\n|---|---|---|---|---|---|"
    out = [f"# Sessions\n",
           f"_{m['generated_at']} · {m['counts']['waiting']} waiting · "
           f"{m['counts']['active']} active · {len(m['machines'])} machine(s)_\n"]
    out += ["## Waiting on you\n"]
    out += [hdr] + [row(s) for s in m["waiting"]] if m["waiting"] else ["Nothing.\n"]
    out += ["", "## Running\n"]
    out += [hdr] + [row(s) for s in m["active"]] if m["active"] else ["None.\n"]
    if m["recent"]:
        out += ["", "## Recently finished\n", hdr] + [row(s) for s in m["recent"]]
    out += ["", "## Machines\n", "| machine | last reported |", "|---|---|"]
    out += [f"| {h} | {t} |" for h, t in sorted(m["machines"].items())]
    return "\n".join(out) + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    store = Path(sys.argv[1])
    m = merge(store)
    (store / "snapshot.json").write_text(json.dumps(m, indent=2))
    (store / "STATUS.md").write_text(status_md(m))
    print(f"merged {len(m['machines'])} machine(s): "
          f"{m['counts']['waiting']} waiting, {m['counts']['active']} active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
