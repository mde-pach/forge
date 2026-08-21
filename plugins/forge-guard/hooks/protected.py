#!/usr/bin/env python3
"""
Nothing changes the rules without a second pair of eyes.

Most of this repo decides how everything else behaves — hooks, settings,
checks, the registry, the kernel, the templates a scaffold ships. Editing any
of it is how a gate gets quietly disabled, and it is exactly where the session
doing the editing is least able to judge itself. So protection is the default
and exposure is the exception: what a session may change without review is the
short list (prose, mostly), not the other way round.

So: touch one of them, and the turn cannot end until an independent review of
that change has been recorded. Run on Stop, exit 2, which is the one exit code
that means "you are not finished".

The evidence for insisting on independence rather than care: asking a model to
critique its own output has been measured making accuracy *worse* — 5% to 3% on
one task — while the same model with a real external check reached 38%. Fresh
context is not a formality here, it is the entire mechanism.

The review is recorded by writing a file whose name fingerprints the reviewed
content; a subagent with fresh context produces it. Reviews expire when the
protected files change again, so one review cannot cover a later edit. The
file must quote, verbatim, the prompt the reviewer was given: independence the
guard cannot verify can at least be made auditable, and the one recorded review
that survived a real session turned out to have been handed its verdict in its
prompt ("found it sound overall ... trust this, don't re-derive it") - visible
only in a transcript nobody reads. Now it would be visible in the review.

This blocks, so it can loop. It did: one session attempted to end its turn 45
times in fourteen minutes, blocked identically every time, because its review
was running in the background and a blocked Stop is how you wait when waiting
is forbidden. The same release valve the gate uses applies here - after 3
consecutive blocks on the SAME outstanding fingerprint, the turn is released
once, loudly, and the guard re-arms - because a blocker that can spin forever
eventually will, at the worst moment. FORGE_GATE_NO_RELEASE disables the valve
where there is no human to unblock (CI), same as the gate.

This paragraph used to say `forge review` produces it. No such command has ever
existed - the registry declares three, and none of them is that. The message
this hook actually prints is self-contained and was always right; the docstring
was describing a command someone intended to build.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# An allowlist, inverted: everything rule-bearing is protected, and what is
# left exposed is a deliberate, short list (docs/, README.md, FRICTIONS.md,
# lockfiles). This used to be the other way round - a list of special files -
# and the gap was exploited within a day of mattering: a session re-scoped a
# check in src/forge/checks/ mid-run, unreviewed, ninety seconds after saying
# it wouldn't, because adding an icon needed a review and rewriting a checker
# needed none. The checks, the registry, the kernel, the contract, the
# templates a scaffold ships (their .claude/ dirs carry the very gate
# fragments this repo sources), and .gitignore - which can HIDE a file from
# every check built on `git status` - all decide behaviour, so they are all in.
PROTECTED = (
    ".claude/",
    ".claude-plugin/",
    "plugins/",
    ".github/",
    "CLAUDE.md",
    "pyproject.toml",
    "package.json",
    ".gitignore",
    "src/forge/",
    "kernel/",
    "contract/",
    "stacks/",
)

# Recording a review writes under .claude/, which is protected - unexempted,
# the act of satisfying the guard would change the fingerprint and demand a
# review of the review, forever. The release counter is exempt for the same
# reason with a sharper edge: it changes on every blocked attempt, so counting
# it would give each block a fresh fingerprint and the release could never
# reach three - the valve would be sealed by its own bookkeeping. The gate's
# counter (.gate-state) is the same file one mechanism over, written in the
# same Stop cycle, and was caught missing from this list by review - sealed
# valve, second edition. (Both are also git-ignored here, but a project using
# this plugin without those lines must not inherit a sealed valve.)
#
# What this cannot see: .git/info/exclude, core.excludesFile and
# `git update-index --assume-unchanged` all hide files from `git status`, so
# protecting .gitignore closes the committed door, not the local ones.
EXEMPT = (".claude/reviews/", ".claude/.guard-state", ".claude/.gate-state")

REVIEW_DIR = ".claude/reviews"

# The loop-release valve, mirroring the gate's (.claude/.gate-state): counts
# consecutive blocks on one outstanding fingerprint. The fingerprint is already
# the digest - it identifies the exact demand being repeated - so unlike the
# gate there is nothing to normalise.
STATE = ".claude/.guard-state"
RELEASE_AFTER = 3


def _release(root: Path, fp: str) -> bool:
    """One more block on `fp`. True when this one should release instead."""
    if os.environ.get("FORGE_GATE_NO_RELEASE"):
        return False  # in CI a release would turn a red build green
    state = root / STATE
    try:
        prev, raw = state.read_text().split()
        count = int(raw)
    except (OSError, ValueError):
        prev, count = "", 0
    count = count + 1 if prev == fp else 1
    if count >= RELEASE_AFTER:
        state.unlink(missing_ok=True)  # re-arm: the next turn is guarded again
        return True
    try:
        state.write_text(f"{fp} {count}\n")
    except OSError:
        pass
    return False


def _clear(root: Path) -> None:
    (root / STATE).unlink(missing_ok=True)


def changed(root: Path) -> list[str]:
    try:
        r = subprocess.run(
            # -uall is load-bearing: without it git collapses a wholly-untracked
            # directory to one `?? .claude/` line, so a brand-new
            # .claude/settings.json is invisible - which is exactly how a hook or
            # a settings file first appears. The guard saw edits to existing
            # protected files and was blind to every new one.
            #
            # -z is equally load-bearing: without it, core.quotePath C-quotes
            # any path with a non-ASCII byte, so `.claude/hooks/evíl.py` came
            # back as `".claude/hooks/ev\303\255l.py"` - leading quote, no
            # prefix match, guard silently passes. One accented character was
            # a full bypass. NUL-separated output is never quoted.
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    out = []
    entries = r.stdout.split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        if status[:1] in ("R", "C"):
            i += 1  # in -z format the SOURCE path follows as its own entry
        if path.startswith(EXEMPT):
            continue
        # "/.claude/" catches every embedded Claude config dir - the stacks
        # templates' hooks and settings ship into scaffolded projects, and the
        # root .claude/ is covered by the prefix list.
        if "/.claude/" in path or any(path == p or path.startswith(p) for p in PROTECTED):
            out.append(path)
    return sorted(out)


def fingerprint(root: Path, files: list[str]) -> str:
    """Identifies the exact content under review, so a review cannot outlive it."""
    h = hashlib.sha256()
    for f in files:
        # NULs delimit name from content and entry from entry: concatenation
        # without them lets distinct (name, content) splits hash identically.
        h.update(f.encode() + b"\0")
        try:
            h.update((root / f).read_bytes())
        except OSError:
            h.update(b"<missing>")
        h.update(b"\0")
    return h.hexdigest()[:16]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    root = (
        Path(payload.get("cwd")) if isinstance(payload, dict) and payload.get("cwd") else Path.cwd()
    )

    files = changed(root)
    if not files:
        _clear(root)
        return 0

    fp = fingerprint(root, files)
    review = root / REVIEW_DIR / f"{fp}.md"
    if review.is_file():
        try:
            has_prompt = "## Prompt" in review.read_text(errors="replace")
        except OSError:
            has_prompt = False
        if has_prompt:
            _clear(root)
            return 0
        complaint = (
            f"A review exists at {REVIEW_DIR}/{fp}.md but it does not contain a"
            " `## Prompt` section\nquoting, verbatim, the prompt the reviewer was"
            " given. Without it there is no way to\naudit whether the reviewer was"
            " independent or was handed its verdict. Add the\nsection with the"
            " exact prompt used, or re-run the review and record both.\n"
        )
    else:
        # Naming the exact tool calls is the closest thing to enforcement a
        # Stop hook has: it cannot force a tool choice, but for a model an
        # instruction that names the call is nearly the call itself. Measured:
        # the prose version of this message ("run a subagent in the
        # foreground") still cost two blocked stops before the session found
        # the blocking wait on its own.
        complaint = (
            "This turn changed files that decide how everything else behaves:\n"
            + "".join(f"  {f}\n" for f in files)
            + "\nThese need an independent review before the turn can end — not a re-read by\n"
            "you, which is measurably worse than no review at all, but a fresh-context pass\n"
            "that has not seen the reasoning behind the change. Do exactly this, now,\n"
            "in this turn:\n\n"
            "1. If a review agent for exactly these files is ALREADY running, do not\n"
            "   start another and do not try to end the turn again. Wait on it:\n"
            "     TaskOutput(task_id=<its id>, block=true, timeout=600000)\n"
            "2. Otherwise launch the reviewer and then wait on it the same way:\n"
            "     Agent(prompt=<the file list and how to see the diff, nothing else —\n"
            "           no prior conclusions, no expected verdict; a primed reviewer\n"
            "           is worse than none>)\n"
            "     TaskOutput(task_id=<its id>, block=true, timeout=600000)\n"
            "   Never poll it, never schedule wakeups, never end the turn while it\n"
            "   runs: that is a spin loop (measured once at 45 blocked stops).\n"
            "3. Record its findings:\n"
            f"     mkdir -p {REVIEW_DIR} && write them to {REVIEW_DIR}/{fp}.md\n"
            "   with a `## Prompt` section quoting, verbatim, the prompt the reviewer\n"
            "   got.\n\n"
            "If your environment has no Agent or TaskOutput tool, any equivalent that\n"
            "runs a fresh-context reviewer and BLOCKS until it returns satisfies this;\n"
            "if your launch tool returns the result directly, that return IS the wait.\n"
            "The file name is a fingerprint of the reviewed content, so editing these\n"
            "files again invalidates the review rather than reusing it.\n"
        )

    if _release(root, fp):
        print(
            json.dumps(
                {
                    "systemMessage": (
                        "forge-guard released on identical block attempt "
                        f"{RELEASE_AFTER} to avoid a loop - the "
                        "protected changes are NOT reviewed, and the guard re-arms "
                        "on the next turn."
                    )
                }
            )
        )
        return 0
    sys.stderr.write(complaint)
    return 2


if __name__ == "__main__":
    # SystemExit is a BaseException, so a bare `except BaseException` here
    # swallowed the exit(2) and turned every block into a pass. The gate printed
    # its refusal and let the turn end anyway - a gate that cannot block, which
    # is the exact failure this file exists to prevent, inside this file.
    try:
        code = main()
    except SystemExit:
        raise
    except Exception:
        code = 0
    sys.exit(code)
