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

**Check it worked:**

```bash
python3 plugins/forge-monitor/doctor.py
```

Read three sections of the output. *EVENTS RECEIVED* should not be empty — if it
is, the plugin isn't loaded, and `claude --debug` will say why. *FIELD DIFF*
should say `ok` — anything else means Claude Code sends a field under a name the
monitor doesn't read. *STORE* should say `HTTP 200`.

## 5 · See it from your phone

```bash
python3 plugins/forge-monitor/serve.py
bash plugins/forge-monitor/tailscale/expose.sh
```

The first run asks you to enable HTTPS certificates for your tailnet — a
one-time click. `expose.sh` then prints a URL. Open it on your phone and add it
to the home screen; the waiting count appears in the title.

Only devices signed into your tailnet can reach it. Nothing is published to the
internet, no port is opened on your machine, and there is no certificate to
renew. `expose.sh` uses `tailscale serve`, never `tailscale funnel`, and does
not offer funnel as an option.

The dashboard reads the store, not your laptop, so it shows every session on
every machine — and you can run it from any machine, or not at all.

## Turning it off

Remove `enabledPlugins` from the project's `.claude/settings.json`. The store
and the local state directory can be deleted by hand; nothing else was touched.

## When something is wrong

`doctor.py` reads only, changes nothing, and its output is designed to be pasted
somewhere for help. The five failures it distinguishes:

| Symptom in doctor.py | Meaning |
|---|---|
| `EVENTS RECEIVED` empty | the plugin never loaded, or hooks never fired |
| `FIELD DIFF` shows `MISSING` | Claude Code names a field differently than the monitor expects |
| `NOT HANDLED BY THE CODE` | a notification type nobody accounted for |
| `STORE ... HTTP 401/403` | the credential is missing, wrong, or rate limited |
| records `PENDING` | written locally, never published — usually the credential |
