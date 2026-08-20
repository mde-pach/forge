#!/usr/bin/env bash
# forge-guard verifier.
#
# The design claims are: a protected change blocks the turn until an
# independent review is recorded, the review must carry the prompt its reviewer
# was given, a repeated identical block releases once rather than looping
# forever, and the release valve is off where no human can unblock. Until this
# file existed the guard had no check at all - the one mechanism whose whole
# job is second-guessing changes was itself never exercised by anything.
set -uo pipefail

GUARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
ok() { printf '  ok    %s\n' "$1"; pass=$((pass+1)); }
no() { printf '  FAIL  %s\n' "$1"; fail=$((fail+1)); }

# Every proof runs in a scratch git repo, never this one: the guard reads
# `git status` of the payload's cwd, so a scratch repo is a complete world.
mk_repo() {
  local d="$TMP/$1"
  mkdir -p "$d"
  git -C "$d" init -q
  git -C "$d" config user.email verify@forge.invalid
  git -C "$d" config user.name verify
  echo base > "$d/base.txt"
  git -C "$d" add base.txt
  git -C "$d" commit -qm base
  printf '%s' "$d"
}
run_guard() {  # $1 repo -> sets rc, out, err
  local d="$1"
  out=$(printf '{"cwd":"%s"}' "$d" | env -u FORGE_GATE_NO_RELEASE python3 "$GUARD_DIR/hooks/protected.py" 2>"$TMP/err"); rc=$?
  err=$(cat "$TMP/err")
}
fp_of() {  # $1 repo -> the fingerprint the guard would demand
  python3 -c "
import sys; sys.path.insert(0, '$GUARD_DIR/hooks'); import protected
from pathlib import Path
root = Path('$1')
files = protected.changed(root)
print(protected.fingerprint(root, files))"
}

echo "1. an untouched tree passes and a protected change blocks"
clean=$(mk_repo clean)
run_guard "$clean"
[ "$rc" = 0 ] && ok "no protected change exits 0" || no "clean tree exited $rc"
d=$(mk_repo blocked)
mkdir -p "$d/.claude"; echo '{}' > "$d/.claude/settings.json"
run_guard "$d"
{ [ "$rc" = 2 ] && printf '%s' "$err" | grep -q '.claude/settings.json'; } \
  && ok "a new protected file blocks with exit 2 and is named" \
  || no "protected change gave rc=$rc, err: $(printf '%s' "$err" | head -1)"
printf '%s' "$err" | grep -qi 'FOREGROUND' \
  && ok "the block prescribes a foreground reviewer" \
  || no "the block does not tell the session to wait for its reviewer"
printf '%s' "$err" | grep -q 'Do NOT give' \
  && ok "the block forbids handing the reviewer a verdict" \
  || no "nothing warns against priming the reviewer"

echo "1b. a path git would quote is still seen - one accented byte is not a bypass"
# With core.quotePath (the default), `git status --porcelain` C-quotes any
# non-ASCII path, so `.claude/hooks/evíl.py` arrived as `".claude/hooks/..."`
# - leading quote, no prefix match, guard silently passed. Found by review,
# reproduced, fixed with -z. This keeps it fixed.
d=$(mk_repo quoted)
mkdir -p "$d/.claude/hooks"; printf 'x' > "$d/.claude/hooks/evíl.py"
git -C "$d" config core.quotePath true
run_guard "$d"
{ [ "$rc" = 2 ] && printf '%s' "$err" | grep -q 'hooks/ev'; } \
  && ok "a non-ASCII protected path blocks and is named" \
  || no "quoted path bypassed the guard (rc=$rc)"

echo "2. a recorded review with its prompt unblocks; one without does not"
# Ordering note: this section deliberately ends on a PASS, which clears the
# release counter raised by its two blocks. Add a third blocking assertion
# here and the valve opens instead - the test would start asserting the
# opposite of what it means to.
fp=$(fp_of "$d")
mkdir -p "$d/.claude/reviews"
printf '# Review\nFindings.\n' > "$d/.claude/reviews/$fp.md"
run_guard "$d"
{ [ "$rc" = 2 ] && printf '%s' "$err" | grep -q '## Prompt'; } \
  && ok "a review without its reviewer's prompt still blocks, and says why" \
  || no "prompt-less review gave rc=$rc"
printf '# Review\n\n## Prompt\nReview the diff of exactly these files.\n\nFindings.\n' \
  > "$d/.claude/reviews/$fp.md"
run_guard "$d"
[ "$rc" = 0 ] && ok "a review carrying its prompt unblocks" || no "valid review exited $rc"
[ -f "$d/.claude/.guard-state" ] && no "the release counter survived a pass" \
                                 || ok "a pass clears the release counter"

echo "3. an identical block releases on the third attempt, loudly, then re-arms"
d=$(mk_repo loop)
mkdir -p "$d/.claude"; echo '{}' > "$d/.claude/settings.json"
# The gate's own counter churns beside the guard's in a real Stop cycle; if
# either counter file were counted by the guard, every block would carry a
# fresh fingerprint and the valve would be sealed by its own bookkeeping -
# which is exactly how the first version of this test failed, and review
# found the gate-state variant of the same seal.
echo 'digest 1' > "$d/.claude/.gate-state"
run_guard "$d"; r1=$rc
echo 'digest 2' > "$d/.claude/.gate-state"
run_guard "$d"; r2=$rc
echo 'digest 3' > "$d/.claude/.gate-state"
run_guard "$d"; r3=$rc; o3=$out
run_guard "$d"; r4=$rc
[ "$r1$r2" = "22" ] && ok "the first two identical blocks block" || no "got rc $r1,$r2"
{ [ "$r3" = 0 ] && printf '%s' "$o3" | grep -q 'NOT reviewed'; } \
  && ok "the third releases with a message saying the changes are NOT reviewed" \
  || no "third attempt: rc=$r3, out: $o3"
[ "$r4" = 2 ] && ok "the guard re-arms: the next turn blocks again" || no "re-armed rc=$r4"

echo "4. editing the protected files resets the count - a new demand starts over"
d=$(mk_repo reset)
mkdir -p "$d/.claude"; echo '{}' > "$d/.claude/settings.json"
run_guard "$d"; run_guard "$d"
echo '{"a":1}' > "$d/.claude/settings.json"   # new content, new fingerprint
run_guard "$d"; r3=$rc
[ "$r3" = 2 ] && ok "attempt 3 against a CHANGED fingerprint still blocks" \
              || no "changed fingerprint released early (rc=$r3)"

echo "5. where no human can unblock, the valve is off"
d=$(mk_repo ci)
mkdir -p "$d/.claude"; echo '{}' > "$d/.claude/settings.json"
all=0
for i in 1 2 3 4 5; do
  printf '{"cwd":"%s"}' "$d" | FORGE_GATE_NO_RELEASE=1 \
    python3 "$GUARD_DIR/hooks/protected.py" >/dev/null 2>&1; [ $? = 2 ] || all=1
done
[ "$all" = 0 ] && ok "FORGE_GATE_NO_RELEASE blocks on every attempt, forever" \
               || no "the valve released with FORGE_GATE_NO_RELEASE set"

echo "6. protection is the default; the exposed list is short and deliberate"
d=$(mk_repo scope)
mkdir -p "$d/docs/how-to"; echo prose > "$d/docs/how-to/thing.md"; echo readme > "$d/README.md"
run_guard "$d"
[ "$rc" = 0 ] && ok "prose (docs/, README.md) changes freely" || no "prose blocked (rc=$rc)"
mkdir -p "$d/src/forge/checks"; echo 'X = 1' > "$d/src/forge/checks/planted.py"
run_guard "$d"
[ "$rc" = 2 ] && ok "a check edit blocks - the exact hole a session once used, unreviewed" \
              || no "src/forge/checks/ change passed (rc=$rc)"
rm -rf "$d/src"
mkdir -p "$d/stacks/python/template/.claude/hooks"; echo 'exit 0' > "$d/stacks/python/template/.claude/hooks/planted.sh"
run_guard "$d"
[ "$rc" = 2 ] && ok "a template's .claude/ blocks - scaffolds ship it into every project" \
              || no "embedded .claude/ change passed (rc=$rc)"
rm -rf "$d/stacks"
echo 'ignored/' > "$d/.gitignore"
run_guard "$d"
[ "$rc" = 2 ] && ok ".gitignore blocks - it can hide files from every status-based check" \
              || no ".gitignore change passed (rc=$rc)"
rm -f "$d/.gitignore"

echo "7. recording the review does not demand a review of the review"
d=$(mk_repo regress)
mkdir -p "$d/.claude"; echo '{}' > "$d/.claude/settings.json"
run_guard "$d"
fp=$(fp_of "$d")
mkdir -p "$d/.claude/reviews"
printf '# Review\n\n## Prompt\nReview the diff.\n\nFine.\n' > "$d/.claude/reviews/$fp.md"
run_guard "$d"
[ "$rc" = 0 ] \
  && ok "the review file, though under .claude/, is exempt - no infinite regress" \
  || no "writing the review re-triggered the guard (rc=$rc)"

printf '\n%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
