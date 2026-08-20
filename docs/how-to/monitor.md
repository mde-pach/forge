# Set up the session monitor

Follow this once. It takes about five minutes and touches two things: a private
repository, and one block in each project you want watched. Nothing is installed
globally, and nothing is hand-authored — `forge start` writes its own config.

If a step doesn't work, that is a bug in this document or in the monitor, not
something to work around. Note where it broke.

## What you need

- **Claude Code**, and **Python 3.9 or newer** (`python3 --version`)
- **[GitHub CLI](https://cli.github.com)**, for the credential. No personal
  access token is created or stored.
- **[Tailscale](https://tailscale.com/download)**, only if you want the dashboard
  on your phone. Optional — without it everything works on loopback. Setting it
  up is in step 4.

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

## 3 · Enable it in a project

**A project forge scaffolded already has this** — `scaffold.sh` writes it and
tells you it did. Skip to step 4.

For an **existing** project you are retrofitting, commit this to
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
changed hooks, settings, manifests or CI without an independent review. Drop
either line to leave that one out.

This file is **committed**, so it applies to anyone who opens the repository —
which is what lets a cloud session inherit it, and what makes sharing the
repository a decision rather than an accident.

## 4 · Start it

```bash
uv run forge start --store <your-username>/forge-state
```

That is the whole thing. `--store` is needed once: it writes the repository into
forge's state directory and prints the path it wrote to. After that, plain
`uv run forge start`. Run it with no store configured and a terminal attached
and it derives your username from `gh` and offers `<you>/forge-state` as the
default, so the flag is really only for scripts.

Only the repository is stored. The branch, how long to wait between routine
updates, how long a session may go quiet before it is flagged and when finished
sessions are forgotten all have defaults in the code that reads them — writing
them into a config file would be four keys restating four constants, which is
four more places for the value to disagree with itself. To change one, add
`branch`, `min_publish_seconds`, `stale_minutes` or `forget_hours` to that file.

It prints what it can see before serving anything:

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

The `tailnet` line appears only once Tailscale is installed and connected. If it
says `tailscale is not installed, so this is loopback only`, that is not a
failure — the dashboard works, it is just on this machine. Set it up when you
want it on your phone.

### Reaching it from your phone

Four one-time steps.

**1. Install Tailscale on this machine and sign in.**

```bash
# macOS  — the standalone build is the one Tailscale recommends
brew install --cask tailscale
# Linux
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Then check the CLI is reachable, because `forge start` looks for it on `PATH`:

```bash
command -v tailscale && tailscale status
```

If `command -v` finds nothing, you have the Mac App Store build, which keeps the
binary inside the application bundle rather than on `PATH`. Find it with
`ls /Applications/Tailscale.app/Contents/MacOS/` and alias it in your shell
profile. If you hit this, note the exact path — it belongs in
`.claude/skills/scaffold/references/verified-stack-facts.md`, because it is the
kind of fact that otherwise gets rediscovered every time.

**2. Enable HTTPS for your tailnet.** `tailscale serve` needs it, and it is a
one-time setting for the whole tailnet, not per device. In the admin console at
[console.tailscale.com/admin/dns](https://console.tailscale.com/admin/dns),
enable **MagicDNS** first, then **HTTPS Certificates**.

> **Read this before you enable it.** Every TLS certificate on the web is
> recorded in the public Certificate Transparency ledger, and Tailscale is
> explicit that this includes your device names: *"your machine names and your
> tailnet DNS name will be published on a public ledger"*, and *"do not enable
> the HTTPS feature if any of your machine names contain sensitive
> information"*. Your tailnet gets an obscured name like `yak-bebop.ts.net`, but
> the hostname of the laptop you serve from becomes public. No session data is
> exposed — only names — but rename the machine first if its name says something
> you would rather it did not.

**3. Install Tailscale on your phone** and sign in to the **same** tailnet.

**4. Run `uv run forge start` again.** It now prints a `tailnet` line. Open that
URL on your phone and add it to the home screen; the waiting count appears in
the title.

Only devices signed into your tailnet can reach it: nothing is published to the
internet, no port is opened on this machine, and there is no certificate to
renew. It uses `tailscale serve`, never `tailscale funnel` — serve reaches your
own devices, funnel publishes to the open internet, and for session state that
distinction is the whole security model, so funnel is not offered. Stopping
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
