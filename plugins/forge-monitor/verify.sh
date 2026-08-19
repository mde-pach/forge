#!/usr/bin/env bash
# forge-monitor verifier.
#
# The design claim is "a session cannot observe this layer". A claim like that
# is worth exactly as much as the test that fails when it stops being true.
# Every check below is the executable form of one sentence in the README.
set -uo pipefail

MON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
export FORGE_MONITOR_STATE="$TMP/state"
pass=0; fail=0
ok()  { printf '  ok    %s\n' "$1"; pass=$((pass+1)); }
no()  { printf '  FAIL  %s\n' "$1"; fail=$((fail+1)); }

PAYLOAD='{"session_id":"verify","cwd":"/tmp","permission_mode":"bypassPermissions","hook_event_name":"X"}'

echo "1. the emitter is silent on every event"
for ev in SessionStart UserPromptSubmit UserPromptExpansion Notification Stop SessionEnd; do
  out=$(printf '%s' "$PAYLOAD" | bash "$MON_DIR/hooks/emit.sh" "$ev" 2>/dev/null)
  err=$(printf '%s' "$PAYLOAD" | bash "$MON_DIR/hooks/emit.sh" "$ev" 2>&1 >/dev/null)
  if [ -z "$out" ] && [ -z "$err" ]; then ok "$ev writes nothing to stdout or stderr"
  else no "$ev emitted output; the session would see it on context-bearing events"; fi
done

echo "2. the emitter cannot block a turn"
for case in "garbage:not json" "empty:" ; do
  name="${case%%:*}"; body="${case#*:}"
  rc=0; printf '%s' "$body" | bash "$MON_DIR/hooks/emit.sh" Stop >/dev/null 2>&1 || rc=$?
  [ "$rc" = 0 ] && ok "$name input exits 0" || no "$name input exited $rc (2 would block the turn)"
done
rc=0; FORGE_MONITOR_STATE=/proc/nowhere bash "$MON_DIR/hooks/emit.sh" Stop </dev/null >/dev/null 2>&1 || rc=$?
[ "$rc" = 0 ] && ok "unwritable state dir exits 0" || no "unwritable state dir exited $rc"

echo "3. the statusline is silent about the monitor and survives odd input"
line=$(printf '{"model":{"display_name":"Opus 5"},"cost":{"total_cost_usd":1.5},"workspace":{"current_dir":"/a/b"}}' \
  | bash "$MON_DIR/statusline.sh" 2>/dev/null)
case "$line" in *forge-monitor*|*"$TMP"*) no "statusline leaks monitor internals: $line" ;;
  *) ok "statusline shows only session facts: $line" ;; esac
rc=0; printf '{}' | bash "$MON_DIR/statusline.sh" >/dev/null 2>&1 || rc=$?
[ "$rc" = 0 ] && ok "statusline exits 0 on empty input" || no "statusline exited $rc"

echo "4. nothing is installed at user scope"
USER_SETTINGS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
if [ -f "$USER_SETTINGS" ] && grep -q 'forge-monitor\|emit\.sh' "$USER_SETTINGS" 2>/dev/null; then
  no "the monitor is wired into $USER_SETTINGS - it must ship as a plugin, not as global config"
else
  ok "no reference in $USER_SETTINGS (this ships as a plugin, so nothing is global)"
fi

echo "5. the plugin manifest and hook config are valid"
if command -v claude >/dev/null 2>&1; then
  if claude plugin validate "$MON_DIR" >/dev/null 2>&1; then ok "claude plugin validate passes"
  else no "claude plugin validate failed"; fi
else
  printf '  note  claude CLI not present; skipping manifest validation\n'
fi
if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$MON_DIR/hooks/hooks.json" 2>/dev/null; then
  ok "hooks.json parses (a malformed one silently disables the whole plugin)"
else
  no "hooks.json is not valid JSON"
fi
# Every hook command must be the emitter, and must reach it through the plugin
# root placeholder - a hardcoded path breaks the moment the plugin updates.
bad=$(python3 - "$MON_DIR/hooks/hooks.json" <<'PY2'
import json, sys
cfg = json.load(open(sys.argv[1]))
bad = []
for ev, groups in cfg.get("hooks", {}).items():
    for g in groups:
        for h in g.get("hooks", []):
            joined = " ".join([h.get("command", "")] + list(h.get("args", [])))
            if "emit.sh" not in joined or "${CLAUDE_PLUGIN_ROOT}" not in joined:
                bad.append(f"{ev}: {joined}")
print("\n".join(bad))
PY2
)
[ -z "$bad" ] && ok "every hook invokes the emitter via \${CLAUDE_PLUGIN_ROOT}" \
              || no "hook commands are wrong: $bad"

echo "6. no session-facing surface exists for it"
leak=$(find "$MON_DIR" -name 'SKILL.md' -o -name 'manifest.yaml' -o -name '*.mcp.json' 2>/dev/null || true)
[ -z "$leak" ] && ok "monitor/ ships no skill, manifest or MCP server" \
               || no "monitor/ exposes a session-facing surface: $leak"

echo "7. the collector folds events into state"
mkdir -p "$FORGE_MONITOR_STATE"
{
  printf '{"forge_event":"SessionStart","at":"2026-08-19T10:00:00Z","host":"h","session_id":"verify-s1","cwd":"/home/u/api"}\n'
  printf '{"forge_event":"Notification","at":"2026-08-19T10:01:00Z","host":"h","session_id":"verify-s1","cwd":"/home/u/api","notification_type":"permission_prompt"}\n'
  printf '{"forge_event":"SessionStart","at":"2026-08-19T10:02:00Z","host":"h","session_id":"verify-s2","cwd":"/home/u/web"}\n'
} > "$FORGE_MONITOR_STATE/events.ndjson"
python3 "$MON_DIR/collector.py" --once >/dev/null 2>&1 || true

# Assert on the injected sessions by id, not on global counts: this machine may
# legitimately have real sessions running, and a verifier that only passes on an
# idle machine is a verifier nobody runs.
probe() {  # $1 = bucket, $2 = session id -> prints the attention reason or MISSING
  python3 - "$FORGE_MONITOR_STATE/snapshot.json" "$1" "$2" <<'PY2'
import json, sys
snap = json.load(open(sys.argv[1]))
for s in snap.get(sys.argv[2], []):
    if s.get("session_id") == sys.argv[3]:
        print(s.get("attention_reason") or "-")
        break
else:
    print("MISSING")
PY2
}
r=$(probe waiting verify-s1)
[ "$r" = "permission request" ] && ok "the blocked session is waiting, reason: $r" \
                               || no "expected verify-s1 waiting with 'permission request', got '$r'"
r=$(probe active verify-s2)
[ "$r" = "-" ] && ok "the working session is active, with no demand" \
               || no "expected verify-s2 active, got '$r'"
r=$(probe active verify-s1)
[ "$r" = "MISSING" ] && ok "a waiting session is not also counted as active" \
                     || no "verify-s1 appears in both buckets"
grep -q 'permission request' "$FORGE_MONITOR_STATE/STATUS.md" 2>/dev/null \
  && ok "STATUS.md names the reason" || no "STATUS.md missing the attention reason"

echo "8. re-reading is incremental, not cumulative"
python3 "$MON_DIR/collector.py" --once >/dev/null 2>&1 || true
r=$(probe waiting verify-s1)
[ "$r" = "permission request" ] && ok "a second pass is stable" || no "second pass lost the state ('$r')"
off=$(python3 -c "import json;print(json.load(open('$FORGE_MONITOR_STATE/.offset'))['pos'])" 2>/dev/null || echo 0)
[ "${off:-0}" -gt 0 ] && ok "the read offset advanced (events are not re-folded)" \
                      || no "no offset recorded; every pass would replay the whole log"

echo "9. the file sink is a drop-in replacement for github"
cat > "$FORGE_MONITOR_STATE/config.json" <<JSON
{ "sink": { "type": "file", "path": "$TMP/published" } }
JSON
python3 "$MON_DIR/collector.py" --once >/dev/null 2>&1 || true
if [ -s "$TMP/published/STATUS.md" ] && [ -s "$TMP/published/snapshot.json" ]; then
  ok "swapping the sink changed where state lands, and nothing else"
else
  no "file sink produced nothing at $TMP/published"
fi

echo "10. the store, not one machine, is the source of truth"
store="$TMP/store"
mkdir -p "$store/sessions/m1" "$store/sessions/m2"
cat > "$store/sessions/m1/snapshot.json" <<'JSON'
{"generated_at":"t1","counts":{"waiting":1,"active":0,"recent":0},
 "waiting":[{"session_id":"m1a","project":"p1","attention_reason":"needs input","attention_since":"2026-01-01T00:00:00Z"}],
 "active":[],"recent":[]}
JSON
cat > "$store/sessions/m2/snapshot.json" <<'JSON'
{"generated_at":"t2","counts":{"waiting":1,"active":1,"recent":0},
 "waiting":[{"session_id":"m2a","project":"p2","attention_reason":"permission request","attention_since":"2025-12-31T00:00:00Z"}],
 "active":[{"session_id":"m2b","project":"p3","state":"working"}],"recent":[]}
JSON
python3 "$MON_DIR/merge.py" "$store" >/dev/null 2>&1 || true
n=$(python3 -c "import json;print(json.load(open('$store/snapshot.json'))['counts']['waiting'])" 2>/dev/null || echo x)
[ "$n" = 2 ] && ok "two machines merge into one view" || no "expected 2 waiting across machines, got $n"
first=$(python3 -c "import json;print(json.load(open('$store/snapshot.json'))['waiting'][0]['session_id'])" 2>/dev/null || echo x)
[ "$first" = "m2a" ] && ok "the longest-waiting demand is listed first" \
                     || no "expected m2a first (waiting since 2025-12-31), got $first"
hosts=$(python3 -c "import json;print(len(json.load(open('$store/snapshot.json'))['machines']))" 2>/dev/null || echo x)
[ "$hosts" = 2 ] && ok "both machines are named in the merged view" || no "expected 2 machines, got $hosts"

printf '\n%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
