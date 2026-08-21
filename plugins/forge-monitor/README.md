# forge-monitor

See what your sessions are doing, from anywhere, without running anything.

## Model

A **session** is the unit; the machine is a field on its record. Each session
keeps its own record current and publishes it to a private GitHub repository,
the store. The dashboard is a window onto the store: run it anywhere or nowhere.

## How it works

Claude Code fires hooks on session events. This plugin registers one program on
eleven of them. It appends the raw payload to a local log, folds the event into
`sessions/<session-id>.json`, and publishes that file when it changed: at once
for a session starting, ending, failing or asking for you; at a floor otherwise;
as a slow heartbeat when unchanged. Every hook is `async`, so no daemon and
nothing on the critical path of a turn.

```
  session ──hooks──► emit.sh ──► sessions/<id>.json ──PUT──► private repo
                         └─ on SessionStart: sweep.py             │
                                                             GET + ETag
                                                                  ▼
                                                   serve.py ──► dashboard
```

`publish.py` writes one file with one `PUT …/contents/sessions/<id>.json`; no
clone anywhere, and one session owns one path. The dashboard reads the store
with conditional requests, which GitHub does not count against the rate limit.

## Three properties, each a test in `verify.sh`

1. **Silent.** Zero bytes on stdout or stderr on every event, so no session can observe this layer.
2. **Harmless.** Always exits 0, on any input or environment. A monitor fails open.
3. **Session-keyed.** Nothing is stored per machine.

## When a session dies

A closed lid fires no `SessionEnd`. The next session to start sweeps: a record
silent for `stale_minutes` is flagged but keeps its state, because a session
blocked on a permission prompt is silent precisely because it waits for you.
Finished records are deleted after `forget_hours`.

## Setup

Per project, committed in `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "forge": { "source": { "source": "github", "repo": "mde-pach/forge" } }
  },
  "enabledPlugins": { "forge-monitor@forge": true }
}
```

Once:

```bash
gh auth login && gh auth setup-git
gh repo create <you>/forge-state --private
uv run forge start --store <you>/forge-state
```

Optional keys in the state directory's `config.json`: `branch`,
`min_publish_seconds` (120), `heartbeat_publish_seconds` (900),
`stale_minutes` (45), `forget_hours` (72).

## The dashboard

Waiting-on-you first, oldest demand at the top; then running; then recently
finished. Each row has project, machine, directory, duration and a copy button
for `cd <cwd> && claude --resume <id>`. It installs as a PWA and shows the last
snapshot, marked stale, when offline.

## Known holes

- The 409/422 stale-sha retry path has never run against a real store.
- Cloud sessions run the plugin but cannot publish: no credential in the container.
- No notifications; the dashboard answers "what is the state", never "come look".
- No statusline heartbeat (cost, context, rate limits): a plugin cannot install a `statusLine`.
- `sw.js` cache versions are bumped by hand.
- The offline snapshot (hosts, directories) sits in the device's Cache Storage.
