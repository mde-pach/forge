# Set up the session monitor

Five minutes. Touches a private repository and one block in each project you
want watched. If a step fails, that is a bug in this document or in the monitor.

## What you need

- Claude Code and Python 3.9+
- [GitHub CLI](https://cli.github.com), for the credential
- [Tailscale](https://tailscale.com/download), only for the dashboard on your phone

Linux, macOS and Windows (Git Bash or WSL).

## 1 · Get forge

```bash
git clone https://github.com/mde-pach/forge
cd forge
```

## 2 · Create the store

Keep it private: it contains project names and working directories.

```bash
gh auth login
gh auth setup-git
gh repo create <your-username>/forge-state --private
```

`gh auth logout` revokes this at any time.

## 3 · Enable it in a project

A scaffolded project already has this. For an existing project, commit to
`.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "forge": { "source": { "source": "github", "repo": "mde-pach/forge" } }
  },
  "enabledPlugins": {
    "forge-monitor@forge": true,
    "forge-guard@forge": true
  }
}
```

`forge-monitor` records the session; `forge-guard` refuses to end a turn that
changed hooks, settings, manifests or CI without an independent review. Never
install either at user scope: they would load in every project.

## 4 · Start it

```bash
uv run forge start --store <your-username>/forge-state
```

`--store` is needed once; it is written to forge's state directory. Optional
keys in the same `config.json`: `branch`, `min_publish_seconds`,
`heartbeat_publish_seconds`, `stale_minutes`, `forget_hours`.

```
readiness
  state      ~/.local/state/forge-monitor (3 local record(s))
  store      mde-pach/forge-state@main - 3 session record(s)

reach
  local      http://127.0.0.1:7373
  tailnet    https://laptop.tail1234.ts.net/
```

The `store` line is the diagnostic. `not configured`: this machine only. `no
token was found`: the four places it looked are listed. `refused the token
(403)`: the credential needs `contents` on that repository. The view opens in
every case with what it has.

### On your phone

1. Install Tailscale on this machine and sign in (`brew install --cask tailscale`
   or `curl -fsSL https://tailscale.com/install.sh | sh`, then `sudo tailscale up`).
   The Mac App Store build keeps the binary in the bundle; alias
   `/Applications/Tailscale.app/Contents/MacOS/Tailscale`.
2. In [the admin console](https://console.tailscale.com/admin/dns) enable
   MagicDNS, then HTTPS Certificates. Certificates are logged publicly with
   your machine name; rename the machine first if that matters.
3. Install Tailscale on your phone, same tailnet.
4. Run `uv run forge start` again and open the `tailnet` URL. Add it to the
   home screen; it installs as an app and shows the last snapshot offline.

Only devices on your tailnet can reach it (`tailscale serve`, never `funnel`).
Stopping `forge start` removes the mapping.

## Turning it off

Remove `enabledPlugins` from the project's `.claude/settings.json`. Delete the
store and the state directory by hand if you want them gone.
