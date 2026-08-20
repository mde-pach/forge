# Set up the session monitor

Follow this once. It takes about five minutes and touches three things: a
private repository, a config file, and one block in each project you want
watched. Nothing is installed globally.

If a step doesn't work, that is a bug in this document or in the monitor, not
something to work around. Note where it broke.

## What you need

- **Claude Code**, and **Python 3.9 or newer** (`python3 --version`)
- **[GitHub CLI](https://cli.github.com)**, for the credential. No personal
  access token is created or stored.
- **[Tailscale](https://tailscale.com/download)**, only for step 5 — reaching
  the dashboard from your phone.

Linux, macOS and Windows are all supported. On Windows, run the commands in Git
Bash or WSL.

## 1 · Get forge

```bash
git clone https://github.com/mde-pach/forge
cd forge
```

## 2 · Create the store

Session state lives in a repository of your own. Keep it **private** — it
contains your project names and working directories.

```bash
gh auth login          # device flow; nothing is typed or stored by forge
gh auth setup-git      # lets git and the monitor authenticate as you
gh repo create <your-username>/forge-state --private
```

`gh auth logout` revokes this at any time.

## 3 · Point the monitor at it

Create `config.json` in the monitor's state directory. That directory differs by
platform — this prints yours:

```bash
python3 plugins/forge-monitor/paths.py 2>/dev/null || \
python3 -c "import sys;sys.path.insert(0,'plugins/forge-monitor');import paths;print(paths.state_dir())"
```

Typically `~/.local/state/forge-monitor` on Linux,
`~/Library/Application Support/forge-monitor` on macOS,
`%LOCALAPPDATA%\forge-monitor` on Windows.

Put this in `config.json` there:

```json
{
  "store": { "repo": "<your-username>/forge-state", "branch": "main" },
  "min_publish_seconds": 120,
  "stale_minutes": 45,
  "forget_hours": 72
}
```

The three numbers are: how long to wait between routine updates, how long a
session may go quiet before it is flagged, and when finished sessions are
forgotten. The defaults are guesses — change them once you have seen real data.

## 4 · Enable it in a project

In any project you want watched, commit this to `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "forge": { "source": { "source": "github", "repo": "mde-pach/forge" } }
  },
  "enabledPlugins": { "forge-monitor@forge": true }
}
```

Because it is in the repository rather than your machine, it follows the project
— including into [cloud sessions](/how-to/start-a-project), which read the repo
and never your laptop.

Start a session in that project, say anything, and let it finish a turn.

## 5 · Look at it

```bash
uv run forge start
```

That is the whole thing. It prints what it can see before serving anything:

```
readiness
  state      ~/.local/state/forge-monitor (3 local record(s))
  store      mde-pach/forge-sessions@main - 3 session record(s)

reach
  local      http://127.0.0.1:7373
  tailnet    https://laptop.tail1234.ts.net/
```

The `store` line is the one that matters. `not configured` means this machine's
sessions only; `no token was found` names the four places it looked; `refused
the token (403)` means the credential needs `contents` on that repository and
nothing broader. In every case the view still opens and shows what it has — it
is a window, not a gate, so it degrades rather than refusing.

The tailnet line appears when tailscale is installed and connected. The first
run asks you to enable HTTPS certificates for your tailnet — a one-time click.
Open the URL on your phone and add it to the home screen; the waiting count
appears in the title. Only devices signed into your tailnet can reach it:
nothing is published to the internet, no port is opened on your machine, and
there is no certificate to renew. It uses `tailscale serve`, never
`tailscale funnel`, and does not offer funnel as an option. Stopping
`forge start` takes the mapping down again.

The dashboard reads the store, not your laptop, so it shows every session on
every machine — and you can run it from any machine, or not at all.

## Turning it off

Remove `enabledPlugins` from the project's `.claude/settings.json`. The store
and the local state directory can be deleted by hand; nothing else was touched.

## When something is wrong

There is no separate diagnostic command. There was one — `forge doctor` — and a
readiness report you have to already know about, and remember to run, is a
report nobody reads. `forge start` prints it every time instead.

| What you see | Meaning |
|---|---|
| `store  not configured` | no `store.repo` in `config.json`; nothing is published |
| `store  ... no token was found` | none of `FORGE_MONITOR_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN` or `gh auth token` produced one |
| `store  ... refused the token (403)` | the credential lacks `contents` on that repository. It is not retried with a broader scope |
| `store  ... unreachable (network)` | the last state read is still shown |
| `0 local record(s)` and an empty page | the plugin never loaded or the hooks never fired — `claude --debug` says why |
