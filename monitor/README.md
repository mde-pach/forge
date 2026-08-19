# forge-monitor

Session monitoring that the session cannot see.

## The constraint that shaped this

> "the agent/session himself shouldn't have any knowledge of this layer.
> everything must be totally separated and enforced by other automated
> mechanism not on the agent hand… the agent/session context and usage must not
> be polluted by this mechanism"

That rules out the obvious designs. Not a skill, not an MCP server, not a tool,
not a `CLAUDE.md` instruction to report status, not a capability. All of those
work by asking the agent to participate, which costs context and — worse —
makes the observation only as reliable as the agent's compliance.

**So this is not a capability.** Capabilities are things a session invokes.
This is something a session is *subject to*. It ships outside
`capabilities/`, has no `manifest.yaml` and no `SKILL.md`, and forge's own CI
asserts that it never grows one.

## Why it can be invisible

Claude Code's hook contract makes it mechanically possible:

> "Stdout is written to the debug log only, not shown in the transcript. Claude
> never sees it."
> — [hooks](https://code.claude.com/docs/en/hooks)

Three events are exceptions, where stdout *is* injected as context:
`SessionStart`, `UserPromptSubmit`, `UserPromptExpansion`. So the emitter prints
nothing, ever, and the installer does not subscribe to two of the three at all.
Not subscribing is a stronger guarantee than remembering to stay quiet.

The statusline is the second invisible channel, and the richest: the runtime
pipes session id, cwd, model, cost, context-window usage, rate limits, git
worktree and PR state into it every turn, and renders the result as chrome for
the human. The model never sees it.

## Shape

```
  session (knows nothing)
     │
     │  hooks: SessionStart/End, Notification, Stop/StopFailure,
     │         Subagent*, Task*, TeammateIdle, PreCompact
     │  statusline: per-turn heartbeat
     ▼
  emit.sh ──append──► events.ndjson        (local, no network, always exit 0)
                            │
                            ▼
                      collector.py          ← separate process, its own identity
                       │        │
                       │        └─ polls `claude agents --json --all`
                       ▼
                    sinks/*.sh              ← the replaceable edge
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
     github.sh                   file.sh
   private state repo        a local directory
```

Three properties, each of them a test in `verify.sh` rather than a promise:

1. **Silent.** The emitter writes zero bytes to stdout and stderr on every
   event, including the three context-bearing ones.
2. **Harmless.** It always exits 0 — on malformed input, on no input, on an
   unwritable state directory. Exit 2 is a *blocking* error on several events;
   a monitor that can stop a turn eventually will, at the worst moment. This
   inverts the rule the quality gates use, on purpose: a gate must fail closed,
   a monitor must fail open.
3. **Separable.** The sink is a process with a one-object stdin contract, not
   an import. `file.sh` is twelve lines and exists to prove that replacing the
   backend touches nothing else.

The agent also cannot *reach* the state store: publishing happens in the
collector, with a credential in the collector's own config, absent from every
session's environment. The observer is not the observed.

## Install

```bash
bash monitor/install.sh                 # writes ~/.claude/settings.json only
bash monitor/verify.sh                  # 21 checks, all of them executable
python3 monitor/collector.py --watch    # or --once from cron/systemd
bash monitor/install.sh --uninstall     # restores the same file
```

`install.sh` never touches a project's `.claude/`, so the monitor is in no
repository and no clone. It is idempotent: installing twice leaves eleven hook
entries, not twenty-two, and `verify.sh` checks that too.

Point it somewhere by editing `config.json` in the state directory:

```json
{ "sink": { "type": "github",
            "repo": "you/forge-state",
            "token_file": "~/.config/forge-monitor/token" } }
```

## What it does not do

- **It does not cover cloud sessions.** `~/.claude/settings.json` is not read by
  Claude Code on the web, and `claude agents` spans the local machine only. A
  cloud session is visible in the Code tab natively but not here. Closing that
  gap means repo-level hooks, which a session *can* read — a real tension with
  the constraint above, not something to paper over.
- **It does not push.** Real-time "something needs you" is already native
  (Remote Control's *Push when actions required*). This layer answers the
  different question: what is running, where, and what has been waiting how
  long.
- **It is not real-time.** State moves at collector cadence, 30s by default.
