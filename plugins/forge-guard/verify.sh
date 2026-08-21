#!/usr/bin/env bash
# forge-guard verifier. Claims: a protected change blocks the turn until a
# review carrying its prompt is recorded; identical blocks release once after
# three, then re-arm; the valve is off under FORGE_GATE_NO_RELEASE.
set -uo pipefail

GUARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
ok() { printf '  ok    %s\n' "$1"; pass=$((pass+1)); }
no() { printf '  FAIL  %s\n' "$1"; fail=$((fail+1)); }

# Every proof runs in a scratch git repo; the guard reads `git status` of the payload's cwd.
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
# The message names the exact tool calls; prose alone was measured insufficient.
printf '%s' "$err" | grep -q 'TaskOutput(task_id=<id>, block=true' \
  && ok "the block names the exact blocking wait call" \
  || no "the block does not name TaskOutput(block=true)"
printf '%s' "$err" | grep -q 'Agent(prompt=' \
  && ok "the block names the exact reviewer launch call" \
  || no "the block does not name the Agent call"
printf '%s' "$err" | grep -q 'ALREADY running' \
  && ok "the block handles a reviewer already in flight" \
  || no "a second block would relaunch instead of waiting"
printf '%s' "$err" | grep -q 'no prior conclusions, no expected verdict' \
  && ok "the block forbids handing the reviewer a verdict" \
  || no "nothing warns against priming the reviewer"

echo "1b. a path git would C-quote is still seen"
d=$(mk_repo quoted)
mkdir -p "$d/.claude/hooks"; printf 'x' > "$d/.claude/hooks/evíl.py"
git -C "$d" config core.quotePath true
run_guard "$d"
{ [ "$rc" = 2 ] && printf '%s' "$err" | grep -q 'hooks/ev'; } \
  && ok "a non-ASCII protected path blocks and is named" \
  || no "quoted path bypassed the guard (rc=$rc)"

echo "2. a recorded review with its prompt unblocks; one without does not"
# This section must end on a pass: a third block here would open the valve.
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
# The gate's counter churns beside the guard's; it must not change the fingerprint.
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

echo "4. editing the protected files resets the count"
d=$(mk_repo reset)
mkdir -p "$d/.claude"; echo '{}' > "$d/.claude/settings.json"
run_guard "$d"; run_guard "$d"
echo '{"a":1}' > "$d/.claude/settings.json"
run_guard "$d"; r3=$rc
[ "$r3" = 2 ] && ok "attempt 3 against a changed fingerprint still blocks" \
              || no "changed fingerprint released early (rc=$r3)"

echo "5. where no human can unblock, the valve is off"
d=$(mk_repo ci)
mkdir -p "$d/.claude"; echo '{}' > "$d/.claude/settings.json"
all=0
for _ in 1 2 3 4 5; do
  printf '{"cwd":"%s"}' "$d" | FORGE_GATE_NO_RELEASE=1 \
    python3 "$GUARD_DIR/hooks/protected.py" >/dev/null 2>&1; [ $? = 2 ] || all=1
done
[ "$all" = 0 ] && ok "FORGE_GATE_NO_RELEASE blocks on every attempt" \
               || no "the valve released with FORGE_GATE_NO_RELEASE set"

echo "6. protection is the default; the exposed list is short"
d=$(mk_repo scope)
mkdir -p "$d/docs/how-to"; echo prose > "$d/docs/how-to/thing.md"; echo readme > "$d/README.md"
run_guard "$d"
[ "$rc" = 0 ] && ok "prose (docs/, README.md) changes freely" || no "prose blocked (rc=$rc)"
mkdir -p "$d/src/forge/checks"; echo 'X = 1' > "$d/src/forge/checks/planted.py"
run_guard "$d"
[ "$rc" = 2 ] && ok "a check edit blocks" || no "src/forge/checks/ change passed (rc=$rc)"
rm -rf "$d/src"
mkdir -p "$d/stacks/python/template/.claude/hooks"; echo 'exit 0' > "$d/stacks/python/template/.claude/hooks/planted.sh"
run_guard "$d"
[ "$rc" = 2 ] && ok "a template's .claude/ blocks" || no "embedded .claude/ change passed (rc=$rc)"
rm -rf "$d/stacks"
echo 'ignored/' > "$d/.gitignore"
run_guard "$d"
[ "$rc" = 2 ] && ok ".gitignore blocks" || no ".gitignore change passed (rc=$rc)"
rm -f "$d/.gitignore"

echo "7. recording the review does not demand a review of the review"
d=$(mk_repo regress)
mkdir -p "$d/.claude"; echo '{}' > "$d/.claude/settings.json"
run_guard "$d"
fp=$(fp_of "$d")
mkdir -p "$d/.claude/reviews"
printf '# Review\n\n## Prompt\nReview the diff.\n\nFine.\n' > "$d/.claude/reviews/$fp.md"
run_guard "$d"
[ "$rc" = 0 ] && ok "the review file, though under .claude/, is exempt" \
              || no "writing the review re-triggered the guard (rc=$rc)"

echo "8. a file may not get denser; a new file may not exceed the tree's median"
admit() { printf '%s' "$1" | python3 "$GUARD_DIR/hooks/admit.py" >/dev/null 2>&1; echo $?; }
printf 'a = 1\nb = 2\n' > "$TMP/e.py"
rc=$(admit "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$TMP/e.py\",\"old_string\":\"a = 1\",\"new_string\":\"# why a is one\\na = 1\"}}")
[ "$rc" = 2 ] && ok "an Edit that raises a file's density is refused" || no "denser Edit rc=$rc"
printf '# one\n# two\na = 1\n' > "$TMP/d.py"
rc=$(admit "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$TMP/d.py\",\"old_string\":\"# two\\n\",\"new_string\":\"\"}}")
[ "$rc" = 0 ] && ok "an Edit that removes prose passes" || no "sparser Edit rc=$rc"
rc=$(admit "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$TMP/d.py\",\"old_string\":\"a = 1\",\"new_string\":\"a = 2\"}}")
[ "$rc" = 0 ] && ok "an Edit that leaves density unchanged passes" || no "neutral Edit rc=$rc"
r=$(mk_repo dens); printf 'x = 1\n' > "$r/lean.py"; printf '# a b c d\ny = 1\n' > "$r/mid.py"
git -C "$r" add . && git -C "$r" commit -qm files
long=$(python3 -c "print(' '.join(['w']*40))")
rc=$(admit "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$r/new.py\",\"content\":\"# $long\\nz = 1\\n\"}}")
[ "$rc" = 2 ] && ok "a new file denser than the tree median is refused" || no "dense new file rc=$rc"
rc=$(admit "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$r/new.py\",\"content\":\"z = 1\\n\"}}")
[ "$rc" = 0 ] && ok "a new file at or below the median passes" || no "lean new file rc=$rc"
printf '# %s\n' "$(python3 -c "print(' '.join(['w']*100))")" > "$TMP/t.py"; for _ in $(seq 100); do echo 'x = 1' >> "$TMP/t.py"; done
out=$(printf '%s' "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$TMP/t.py\",\"old_string\":\"# w \",\"new_string\":\"# w w w w \"}}" | python3 "$GUARD_DIR/hooks/admit.py" 2>/dev/null); rc=$?
{ [ "$rc" = 0 ] && printf '%s' "$out" | grep -q 'Within tolerance'; } \
  && ok "3% denser passes with a warning" || no "3% denser: rc=$rc out=$out"
rc=$(admit "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$TMP/t.py\",\"old_string\":\"# w \",\"new_string\":\"# w w w w w w w w w \"}}")
[ "$rc" = 2 ] && ok "8% denser is refused" || no "8% denser rc=$rc"
rc=$(admit "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$r/x.json\",\"content\":\"{}\"}}")
[ "$rc" = 0 ] && ok "unmeasured kinds pass" || no "json rc=$rc"
rc=$(admit "garbage")
[ "$rc" = 0 ] && ok "garbage input never blocks" || no "garbage rc=$rc"

printf '\n%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
