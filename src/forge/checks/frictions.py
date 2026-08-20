"""
FRICTIONS.md says what is still wrong. Two ways it stops being true.

**A closed row that is still here.** The file's own policy has always been that
a friction is removed once it closes. It was never honoured: the table reached
75 rows, 50 of them closed, so two thirds of a document whose job is to list
outstanding work was outstanding work that had been done. Prose describing a
policy does not enforce it - that is the same lesson as every other check here -
so the policy is read out of the table now and failed on.

**A citation of a row that no longer exists.** Removing closed rows breaks any
file that pointed at one - a scaffold script cited a row about the executable
bit, and several surviving rows cited rows that were about to be deleted. A
dangling citation is worse than no citation: it looks like evidence and resolves
to nothing.

Note that the previous paragraph does not spell that citation out. Written in
full it would BE one, and this file would fail its own check - which is exactly
what happened, in CI, on the commit that introduced it.

One recognised spelling, `friction NN` or `friction #NN`, for the same reason
`uv run forge <cmd>` is the only recognised invocation. Prose that says "row NN"
is deliberately not a citation - it is how a surviving row records that it
absorbed a number that is gone.

What this does NOT check: whether a row that says `open` is actually still open.
Nothing mechanical can know that, and pretending otherwise is how row 12 sat
marked closed for three days while the exposure it describes was live.
"""

from __future__ import annotations

import re

from forge.checks.orphans import repo_files
from forge.registry import ROOT

FRICTIONS = "FRICTIONS.md"
ROW = re.compile(r"^\|\s*(?P<num>\d+)\s*\|[^|]*\|.*\|(?P<status>[^|]*)\|\s*$")
CITATION = re.compile(r"\bfriction\s+#?(?P<num>\d+)\b", re.IGNORECASE)


def rows() -> dict[str, str]:
    """number -> status text, in file order."""
    out: dict[str, str] = {}
    for line in (ROOT / FRICTIONS).read_text(errors="replace").splitlines():
        m = ROW.match(line)
        if m:
            out[m.group("num")] = m.group("status").strip()
    return out


def check() -> list[str]:
    table = rows()
    errs = [
        f"{FRICTIONS} row {num} is marked closed and is still here - "
        f"a closed friction is removed, and git history is the archive"
        for num, status in table.items()
        if status.lower().startswith("closed")
    ]
    if not table:
        errs.append(f"{FRICTIONS} has no rows this check can read - the table format changed")

    for f in repo_files():
        if f.endswith((".png", ".jpg", ".ico", ".woff", ".woff2")):
            continue
        try:
            text = (ROOT / f).read_text(errors="replace")
        except OSError:
            continue
        for num in {m.group("num") for m in CITATION.finditer(text)}:
            if num not in table:
                errs.append(f"{f} cites `friction {num}`, which {FRICTIONS} no longer has")
    return sorted(set(errs))
