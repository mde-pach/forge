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

Nothing goes into `~/.claude`. This is a **plugin**, so it is declared per
project, versioned, and reproduces identically in any environment — including
Claude Code cloud sessions, which read the repo and never your machine.

In a project's `.claude/settings.json`, committed:

```json
{
  "extraKnownMarketplaces": {
    "forge": { "source": { "source": "github", "repo": "mde-pach/forge" } }
  },
  "enabledPlugins": { "forge-monitor@forge": true }
}
```

Then create the store once — this is not optional, it is the only place the
machines meet:

```bash
gh auth login && gh auth setup-git
gh repo create <you>/forge-state --private
```

```json
{ "sink": { "type": "github", "repo": "<you>/forge-state" } }
```

Then, on each machine that should collect:

```bash
bash plugins/forge-monitor/verify.sh            # 26 checks, all executable
bash plugins/forge-monitor/run.sh               # collector + dashboard
bash plugins/forge-monitor/tailscale/expose.sh  # reach it from your phone
```

An earlier version installed hooks into `~/.claude/settings.json`. That was
wrong: global config makes every session on the machine carry the monitor
whether or not the work has anything to do with forge, and it reproduces
nowhere. Packaging gives isolation and reproducibility for free, and it is why
the cloud-session gap closed on its own — a plugin declared in the repo is
installed at session start wherever the session runs.

Point it somewhere by editing `config.json` in the state directory:

```json
{ "sink": { "type": "github", "repo": "you/forge-state" } }
```

**No personal access token is needed.** The GitHub sink prefers git's credential
helper, which `gh` configures once:

```bash
gh auth login          # device flow, no secret typed or stored by us
gh auth setup-git      # points git at gh as its credential helper
gh repo create you/forge-state --private
```

After that a plain `git push` authenticates as you, with nothing on disk to
rotate and `gh auth logout` as the revoke. The sink falls back to `gh auth
token` (read at push time, never written) and only then to a `token_file`, for
machines with no `gh`. It reports which one it used, because a sink that
silently stops publishing is worse than one that says why.

## The dashboard

`serve.py` binds **loopback only** and serves a single-file page: waiting-on-you
first, then running, then recently finished — each with why, which machine, and
how long. It polls every 10s, refreshes on focus, and puts the waiting count in
the title so a home-screen shortcut shows it.

Reaching it from your phone is `tailscale serve`, never `tailscale funnel`:
serve reaches devices on your tailnet, funnel publishes to the internet. For
session state that distinction is the whole security model, so `expose.sh`
does not offer funnel at all. Nothing is published, no port is opened, and
there is no certificate to renew.

`expose.sh` is deliberately generic — it is the reachability primitive for the
rest of the stack too:

```bash
bash tailscale/expose.sh          # the dashboard on 7373
bash tailscale/expose.sh 3000     # a dev server
bash tailscale/expose.sh --status
```

## Why the store is not optional

An earlier version of this README implied the sink was a nice-to-have because
the dashboard could read local state directly. That was wrong, and the reason it
was wrong is structural:

- `claude agents` spans **one machine**, and an event log lives on the disk that
  wrote it. Two machines have no way to see each other except through a shared
  store.
- A **cloud session** runs the plugin — but in an isolated container. Its events
  never reach your laptop's filesystem. Without something that ships them out,
  the cloud coverage the plugin appears to buy is not real (see below).
- With the laptop asleep, a dashboard served *from* the laptop is unreachable.
  The store still holds the last known state.
- State on one disk is state that dies with a reinstall. There is no history.

So the flow is store-first: each machine's collector publishes its own
`sessions/<host>/snapshot.json`, `merge.py` folds every host into one
`snapshot.json`, and the dashboard reads *that*, falling back to local state
only when no store is configured yet. Demands are sorted oldest-first, because
the thing that has been waiting longest is the thing you most need to see.

## The cloud-session hole, stated plainly

Making this a plugin means a cloud session *runs* it. It does not mean the
events arrive: the container is isolated and discarded. Closing that needs a
credential inside the cloud environment so the session can push its own state —
and in a cloud container the agent can read anything the hooks can, so that
credential is reachable by the agent. It should therefore be scoped to the state
repo and nothing else, and the blast radius is "a session could corrupt its own
monitoring data". That is a decision, not a detail, and it is unmade.

## What it does not do

- **It does not push.** Real-time "something needs you" is already native
  (Remote Control's *Push when actions required*). This layer answers the other
  question: what is running, where, and what has been waiting how long.
- **It is not real-time.** State moves at collector cadence, 30s by default.
- **The statusline is opt-in.** A plugin's `settings.json` supports only the
  `agent` and `subagentStatusLine` keys, so `statusline.sh` cannot be installed
  by the plugin. Point your own `statusLine` at it if you want the richer
  per-turn heartbeat (cost, context-window usage, rate limits); the hooks work
  without it.
