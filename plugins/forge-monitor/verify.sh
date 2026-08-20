#!/usr/bin/env bash
# forge-monitor verifier.
#
# The design claims are: a session cannot observe this layer, it can never block
# a turn, the unit is the session rather than the machine, and nothing has to be
# running for the state to stay true. A claim is worth exactly as much as the
# test that fails when it stops holding.
set -uo pipefail

MON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
export FORGE_MONITOR_STATE="$TMP/state"
pass=0; fail=0; skip=0
ok() { printf '  ok    %s\n' "$1"; pass=$((pass+1)); }
no() { printf '  FAIL  %s\n' "$1"; fail=$((fail+1)); }
# A check that cannot run must SAY so. This one silently vanished when `claude`
# was not on PATH, so the summary read 37 locally and 36 in CI with no
# explanation - a count that differs by environment without naming the reason
# is a number nobody can act on, and one check short of the local run is exactly
# how a check that tests nothing hides.
skipped() { printf '  skip  %s (%s)\n' "$1" "$2"; skip=$((skip+1)); }

EV='{"session_id":"verify-1","cwd":"/tmp/proj","permission_mode":"bypassPermissions"}'

echo "1. the emitter is silent on every event"
for ev in SessionStart UserPromptSubmit UserPromptExpansion Notification Stop SessionEnd; do
  out=$(printf '%s' "$EV" | bash "$MON_DIR/hooks/emit.sh" "$ev" 2>/dev/null)
  err=$(printf '%s' "$EV" | bash "$MON_DIR/hooks/emit.sh" "$ev" 2>&1 >/dev/null)
  [ -z "$out" ] && [ -z "$err" ] && ok "$ev writes nothing to stdout or stderr" \
    || no "$ev emitted output; on a context-bearing event the session would see it"
done

echo "2. the emitter cannot block a turn"
for c in "garbage:not json" "empty:"; do
  n="${c%%:*}"; b="${c#*:}"
  rc=0; printf '%s' "$b" | bash "$MON_DIR/hooks/emit.sh" Stop >/dev/null 2>&1 || rc=$?
  [ "$rc" = 0 ] && ok "$n input exits 0" || no "$n input exited $rc (2 would block the turn)"
done
rc=0; FORGE_MONITOR_STATE=/proc/nowhere bash "$MON_DIR/hooks/emit.sh" Stop </dev/null >/dev/null 2>&1 || rc=$?
[ "$rc" = 0 ] && ok "unwritable state dir exits 0" || no "unwritable state dir exited $rc"
# FORGE_MONITOR_STATE is passed through the stripped environment on purpose:
# without it, this test's payload lands in the REAL state dir - eight verify-1
# Stop events were found in a production event log, one per full check run,
# and a verify-1 row can reach the real dashboard. A test that leaks into the
# state it exists to protect is the exact inversion of its job.
rc=0; printf '%s' "$EV" | env -i PATH=/usr/bin:/bin FORGE_MONITOR_STATE="$FORGE_MONITOR_STATE" \
  bash "$MON_DIR/hooks/emit.sh" Stop >/dev/null 2>&1 || rc=$?
[ "$rc" = 0 ] && ok "a stripped environment exits 0" || no "stripped environment exited $rc"
[ -f "$FORGE_MONITOR_STATE/events-Stop.ndjson" ] \
  && ok "the stripped-environment event landed in the harness state dir, not the real one" \
  || no "the stripped-environment event did not reach \$FORGE_MONITOR_STATE - it went somewhere real"

echo "3. every hook runs async, so none is on the critical path"
n=$(python3 -c "
import json;c=json.load(open('$MON_DIR/hooks/hooks.json'))['hooks']
hs=[h for gs in c.values() for g in gs for h in g['hooks']]
print(sum(1 for h in hs if h.get('async') is True), len(hs))")
set -- $n
[ "$1" = "$2" ] && ok "all $2 hooks are async" || no "only $1 of $2 hooks are async"

echo "4. the unit is the session, not the machine"
printf '%s' "$EV" | bash "$MON_DIR/hooks/emit.sh" SessionStart >/dev/null 2>&1
[ -f "$FORGE_MONITOR_STATE/sessions/verify-1.json" ] \
  && ok "state is keyed by session id" || no "no per-session record was written"
[ -d "$FORGE_MONITOR_STATE/machines" ] && no "a machine-keyed directory exists" \
  || ok "nothing is keyed by machine"
h=$(python3 -c "import json;print(json.load(open('$FORGE_MONITOR_STATE/sessions/verify-1.json')).get('host',''))")
[ -n "$h" ] && ok "the machine is a field on the record ($h), not a structure" \
             || no "the record carries no host field"

echo "4b. uncommitted work is a field on the record, not a post-mortem discovery"
wt="$TMP/worktree"; mkdir -p "$wt"
git -C "$wt" init -q 2>/dev/null
git -C "$wt" config user.email v@v; git -C "$wt" config user.name v
echo base > "$wt/base.txt"; git -C "$wt" add base.txt; git -C "$wt" commit -qm base
echo a > "$wt/a.txt"; echo b > "$wt/b.txt"
printf '{"session_id":"d-1","cwd":"%s"}' "$wt" | python3 "$MON_DIR/record.py" Stop >/dev/null
dirty=$(python3 -c "import json;print(json.load(open('$FORGE_MONITOR_STATE/sessions/d-1.json')).get('dirty_files'))")
[ "$dirty" = 2 ] && ok "two untracked files are counted on the record" \
                 || no "dirty_files was '$dirty', expected 2"
rm -f "$wt/a.txt" "$wt/b.txt"
printf '{"session_id":"d-1","cwd":"%s"}' "$wt" | python3 "$MON_DIR/record.py" Stop >/dev/null
dirty=$(python3 -c "import json;print(json.load(open('$FORGE_MONITOR_STATE/sessions/d-1.json')).get('dirty_files'))")
[ "$dirty" = 0 ] && ok "a clean tree counts zero" || no "clean tree counted '$dirty'"
nogit="$TMP/nogit"; mkdir -p "$nogit"
printf '{"session_id":"d-2","cwd":"%s"}' "$nogit" | python3 "$MON_DIR/record.py" Stop >/dev/null
absent=$(python3 -c "import json;print('dirty_files' in json.load(open('$FORGE_MONITOR_STATE/sessions/d-2.json')))")
[ "$absent" = False ] && ok "a cwd that is not a git repo carries no count, and nothing breaks" \
                      || no "non-git cwd produced a dirty_files field"

echo "5. publishing needs a difference, and attention never waits"
r() { printf '{"session_id":"c-1"%s}' "$1" | python3 "$MON_DIR/record.py" "$2"; }
a=$(r '' SessionStart); b=$(r '' Stop); c=$(r ',"notification_type":"agent_needs_input"' Notification)
[ "$a" = publish ] && ok "a session starting publishes" || no "SessionStart said '$a'"
[ "$b" = hold ]    && ok "a routine turn end is held back" || no "Stop said '$b', expected hold"
[ "$c" = publish ] && ok "an attention event publishes immediately" || no "Notification said '$c'"
# A demand already published does not publish again just because the event
# repeats - the first monitored session put seven commits in the store that
# differed only in last_seen. Content, not cadence.
d=$(r ',"notification_type":"agent_needs_input"' Notification)
[ "$d" = hold ] && ok "the same demand repeated is held - no commit spam" \
                || no "a repeated identical demand said '$d'"
# A Stop that a Stop hook forced to continue is work, not rest.
e=$(r ',"stop_hook_active":true' Stop)
st=$(python3 -c "import json;print(json.load(open('$FORGE_MONITOR_STATE/sessions/c-1.json'))['state'])")
[ "$st" = working ] && ok "a hook-blocked Stop records the session as working, not idle" \
                    || no "hook-blocked Stop recorded state '$st'"
# An unchanged record still publishes eventually: the heartbeat keeps the
# store's last_seen honest without a change to ride on.
python3 - "$FORGE_MONITOR_STATE/sessions/c-1.json" <<'PYHB'
import json, sys
from datetime import datetime, timezone, timedelta
p = sys.argv[1]; r = json.load(open(p))
r["publish_attempted_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1200)).strftime("%Y-%m-%dT%H:%M:%SZ")
open(p, "w").write(json.dumps(r))
PYHB
f=$(r ',"stop_hook_active":true' Stop)
[ "$f" = publish ] && ok "an unchanged record heartbeats after the quiet interval" \
                   || no "heartbeat said '$f'"

echo "6. a silent session is flagged, never hidden"
mkdir -p "$FORGE_MONITOR_STATE/sessions"
python3 - "$FORGE_MONITOR_STATE" <<'PY'
import json, sys, pathlib
from datetime import datetime, timezone, timedelta
d = pathlib.Path(sys.argv[1]) / "sessions"
old = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
gone = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
(d/"blocked-old.json").write_text(json.dumps({"session_id":"blocked-old","state":"blocked",
  "attention_reason":"needs input","needs_attention":True,"last_seen":old}))
(d/"ended-old.json").write_text(json.dumps({"session_id":"ended-old","state":"ended",
  "ended":True,"last_seen":gone}))
PY
python3 "$MON_DIR/sweep.py" verify-1 >/dev/null 2>&1 || true
st=$(python3 -c "
import json;r=json.load(open('$FORGE_MONITOR_STATE/sessions/blocked-old.json'))
print(r.get('state'), r.get('needs_attention'), r.get('stale'))")
[ "$st" = "blocked True True" ] \
  && ok "a session waiting 3h stays in the waiting list, marked stale" \
  || no "the sweep changed a waiting session to '$st'; it must flag, not hide"
[ -f "$FORGE_MONITOR_STATE/sessions/ended-old.json" ] \
  && no "a 5-day-old finished session was not forgotten" \
  || ok "finished records are forgotten once they are noise"

echo "7. the dashboard reads the store, and degrades rather than blanking"
snap() {  # $1 = state dir -> prints {"source":..,"waiting":[..]}
  python3 - "$MON_DIR" "$1" <<'PYSNAP'
import json, sys, importlib.util, pathlib
spec = importlib.util.spec_from_file_location("srv", pathlib.Path(sys.argv[1]) / "serve.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
h = m.Handler.__new__(m.Handler); h.state = pathlib.Path(sys.argv[2])
s = h._snapshot()
print(json.dumps({"source": s["source"], "waiting": [r["session_id"] for r in s["waiting"]]}))
PYSNAP
}
loc="$TMP/local"; mkdir -p "$loc/sessions"
python3 - "$loc/sessions" <<'PYFIX'
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
(d/"s-a.json").write_text(json.dumps({"session_id":"s-a","host":"laptop","project":"api",
  "state":"blocked","attention_reason":"needs input","needs_attention":True,
  "attention_since":"2026-01-01T00:00:00Z","last_seen":"2026-01-01T00:05:00Z"}))
(d/"s-b.json").write_text(json.dumps({"session_id":"s-b","host":"desktop","project":"web",
  "state":"blocked","attention_reason":"permission request","needs_attention":True,
  "attention_since":"2025-12-31T00:00:00Z","last_seen":"2026-01-01T00:06:00Z"}))
PYFIX
out=$(snap "$loc")
echo "$out" | grep -q '"waiting": \["s-b", "s-a"\]' \
  && ok "two sessions on two machines are just two sessions, oldest demand first" \
  || no "wrong waiting order: $out"
echo "$out" | grep -q '"source": "local"' \
  && ok "with no store configured it still shows this machine" || no "unexpected source: $out"

# A configured but unreachable store must not blank the page.
echo '{"store":{"repo":"mde-pach/definitely-not-a-repo-xyz"}}' > "$loc/config.json"
out=$(snap "$loc")
echo "$out" | grep -qE '"source": "(local|store \(stale\))"' \
  && ok "an unreachable store degrades instead of blanking" || no "unreachable store gave: $out"

echo "7b. publishing needs no clone, and retries by being pending"
{ [ -f "$MON_DIR/publish.py" ] && [ ! -f "$MON_DIR/publish.sh" ]; } \
  && ok "publishing is an API call, not a git clone" || no "the git publisher is still here"
if grep -q 'git clone' "$MON_DIR"/*.py "$MON_DIR"/hooks/*.sh 2>/dev/null; then
  no "something still clones the store"
else
  ok "nothing clones the store"
fi
pend="$TMP/pend"; mkdir -p "$pend/sessions"
printf '{"session_id":"p1","state":"working","last_seen":"2026-01-02T00:00:00Z","published_at":"2026-01-01T00:00:00Z"}' > "$pend/sessions/p1.json"
printf '{"session_id":"p2","state":"working","last_seen":"2026-01-01T00:00:00Z","published_at":"2026-01-01T00:00:00Z"}' > "$pend/sessions/p2.json"
got=$(python3 -c "
import sys; sys.path.insert(0, '$MON_DIR'); import publish
from pathlib import Path
print(','.join(publish.pending(Path('$pend'))))")
[ "$got" = "p1" ] && ok "a record newer than its last publish is pending; retry needs no queue" \
                  || no "expected pending=p1, got '$got'"
rc=0; FORGE_MONITOR_STATE="$pend" python3 "$MON_DIR/publish.py" --flush >/dev/null 2>&1 || rc=$?
[ "$rc" = 0 ] && ok "publishing with no store or token exits 0 silently" || no "publish exited $rc"
# The store never receives this machine's bookkeeping - in particular not
# published_at, which is stamped AFTER upload and so was always one publish
# stale in the store copy, making every published record declare itself
# unpublished forever by pending()'s own rule.
kept=$(python3 -c "
import sys; sys.path.insert(0, '$MON_DIR'); import publish
r = {'session_id':'u1','state':'ended','last_seen':'2026-01-02T00:00:00Z',
     'published_at':'2026-01-01T00:00:00Z','store_sha':'abc','publish_attempted_at':'x',
     'publish_attempted_hash':'y'}
print(','.join(sorted(publish.upload_payload(r))))")
[ "$kept" = "last_seen,session_id,state" ] \
  && ok "the upload carries no publish stamp or bookkeeping (got: $kept)" \
  || no "the upload leaks bookkeeping: $kept"

echo "8. nothing is installed at user scope, and nothing is session-facing"
US="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
if [ -f "$US" ] && grep -q 'forge-monitor\|emit\.sh' "$US" 2>/dev/null; then
  no "wired into $US - this must ship as a plugin, not as global config"
else ok "no reference in $US"; fi
find "$MON_DIR" -name 'SKILL.md' -o -name 'manifest.yaml' -o -name '*.mcp.json' | grep -q . \
  && no "a session-facing surface exists" || ok "ships no skill, manifest or MCP server"
if command -v claude >/dev/null 2>&1; then
  claude plugin validate "$MON_DIR" >/dev/null 2>&1 \
    && ok "claude plugin validate passes" || no "claude plugin validate failed"
else
  skipped "claude plugin validate" "claude is not on PATH"
fi
bad=$(python3 - "$MON_DIR/hooks/hooks.json" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
print("\n".join(f"{ev}: {j}" for ev, gs in cfg.get("hooks", {}).items() for g in gs
                for h in g.get("hooks", [])
                for j in [" ".join([h.get("command","")] + list(h.get("args", [])))]
                if "emit.sh" not in j or "${CLAUDE_PLUGIN_ROOT}" not in j))
PY
)
[ -z "$bad" ] && ok "every hook reaches the emitter via \${CLAUDE_PLUGIN_ROOT}" || no "bad hooks: $bad"

echo "9. no daemon is required for the state to be true"
if [ -f "$MON_DIR/collector.py" ] || [ -f "$MON_DIR/merge.py" ] || [ -f "$MON_DIR/run.sh" ]; then
  no "a background process is back"
else
  ok "no collector, no merge step, no daemon"
fi

echo "10. the hook path runs on Linux, macOS and Windows"
gnu=$(grep -nE '(^|[^[:alnum:]_])(timeout|readlink -f|mapfile|realpath) ' \
        "$MON_DIR/hooks/emit.sh" "$MON_DIR/hooks/emit.py" 2>/dev/null || true)
[ -z "$gnu" ] && ok "no GNU-only commands in the hook path (macOS ships none of them)" \
              || no "GNU-only commands would fail on macOS: $gnu"
if sh -n "$MON_DIR/hooks/emit.sh" 2>/dev/null; then
  ok "the launcher is POSIX sh (macOS bash is 3.2, Windows may have neither)"
else
  no "the launcher is not valid POSIX sh"
fi
bashism=$(grep -nE '\[\[|BASH_SOURCE|\$\{[A-Za-z_]+\/\/' "$MON_DIR/hooks/emit.sh" || true)
[ -z "$bashism" ] && ok "the launcher contains no bashisms" || no "bashisms in the launcher: $bashism"
# Parsed, not grepped: the previous version matched the comment explaining why
# os.uname() is avoided, which is the same mistake as deciding on tool output
# instead of exit codes.
if python3 - "$MON_DIR" <<'PYAST'
import ast, pathlib, sys
bad = []
for f in sorted(pathlib.Path(sys.argv[1]).glob("*.py")):
    for node in ast.walk(ast.parse(f.read_text())):
        if isinstance(node, ast.Attribute) and node.attr == "uname":
            bad.append(f"{f.name}:{node.lineno}")
if bad:
    print(" ".join(bad)); sys.exit(1)
PYAST
then
  ok "no os.uname() call; the hostname comes from platform.node()"
else
  no "os.uname() is POSIX-only and would raise on Windows"
fi
if python3 -c "
import sys; sys.path.insert(0, '$MON_DIR'); import paths, os
assert paths.state_dir(), 'no state dir'
assert paths.hostname(), 'no hostname'
" 2>/dev/null; then
  ok "the state directory resolves on this platform"
else
  no "paths.state_dir() failed"
fi
launch=$(printf '{"session_id":"launch-1","cwd":"/tmp/x"}' | sh "$MON_DIR/hooks/emit.sh" Stop 2>&1; echo "rc=$?")
case "$launch" in
  "rc=0") ok "the launcher runs the hook and stays silent" ;;
  *) no "launcher output was: $launch" ;;
esac

echo "11. a captured payload folds into the fields the record promises"
# The fixtures are real hook payloads, sanitized (ids and paths replaced, field
# names untouched - the field names ARE the fixture). They exist because the
# first record ever published carried end_reason: null: record.py read a field
# no payload has ever contained, and nothing compared the code to a payload.
# This is that comparison. An event with no captured payload yet is a skip that
# says so, not a silent pass - SessionStart has never been observed to fire,
# which is an open question, so its fixture cannot honestly exist yet.
FIX="$MON_DIR/fixtures"
fold_field() {  # $1 payload file, $2 event, $3 field -> value, or MISSING when null/absent
  FORGE_MONITOR_STATE="$TMP/fold-$(basename "$1" .json)" python3 - "$MON_DIR" "$1" "$2" "$3" <<'PYFOLD'
import json, sys
sys.path.insert(0, sys.argv[1])
import record, paths
p = json.load(open(sys.argv[2]))
record.handle(sys.argv[3], p)
rec = json.loads((paths.state_dir() / "sessions" / (p["session_id"] + ".json")).read_text())
v = rec.get(sys.argv[4])
print("MISSING" if v is None else v)
PYFOLD
}
for spec in "SessionEnd:end_reason" "Stop:last_message" "Notification:attention_reason" \
            "SessionStart:start_reason"; do
  ev="${spec%%:*}"; field="${spec#*:}"
  if [ -f "$FIX/events-$ev.json" ]; then
    got=$(fold_field "$FIX/events-$ev.json" "$ev" "$field")
    [ "$got" != "MISSING" ] \
      && ok "$ev's payload populates $field ($got)" \
      || no "$ev folded but $field is null - record.py reads a field the payload does not carry"
  else
    skipped "$ev payload populates $field" "no captured payload yet"
  fi
done
# The break this check must notice: the same payload with its load-bearing
# field renamed must fail. Assembled at run time, not committed - a fixture
# whose job is to be wrong would be a file waiting to be mistaken for a shape.
python3 -c "
import json
p = json.load(open('$FIX/events-SessionEnd.json'))
p['renamed_away'] = p.pop('reason')
open('$TMP/broken-SessionEnd.json', 'w').write(json.dumps(p))"
got=$(fold_field "$TMP/broken-SessionEnd.json" SessionEnd end_reason)
[ "$got" = "MISSING" ] \
  && ok "a renamed payload field is noticed (this check can actually fail)" \
  || no "the broken payload still produced end_reason='$got'; the check proves nothing"

if [ "$skip" -gt 0 ]; then
  printf '\n%s passed, %s failed, %s skipped\n' "$pass" "$fail" "$skip"
else
  printf '\n%s passed, %s failed\n' "$pass" "$fail"
fi
[ "$fail" -eq 0 ]
