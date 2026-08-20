# forge-monitor

See what your sessions are doing, from anywhere, without running anything.

## The idea in one paragraph

A **session** is the unit. Not a machine, not an agent — two sessions on two
machines are just two sessions, and which computer they happen to run on is a
field on the record like the working directory. Each session keeps its own
record current, publishes it to a private GitHub repository, and that repository
is the source of truth. A dashboard is a window onto it: run it wherever you
like, or nowhere at all, and the state stays correct either way.

## How it works

Claude Code fires **hooks** — small programs it runs when something happens: a
session starts, it needs your input, a turn ends. This plugin registers one
program on eleven of those events, and it does three things:

1. appends the raw payload to a local log,
2. folds the event into `sessions/<session-id>.json`,
3. sometimes pushes that one file to the store.

"Sometimes" is the interesting part. Pushing on every event would mean thousands
of commits a day, so the policy is: **anything that changes what you would want
to know publishes immediately** — a session starting, ending, failing, or asking
for you — and everything else is rate-limited to one push every two minutes.
Attention never waits, because attention is the entire point.

Every hook is registered `async: true`, so Claude Code does not wait for it.
That is what makes it safe for a hook to touch the network at all, and it is why
there is **no daemon**: nothing has to be running for the state to be true.

## What runs where

```
  a session, which knows none of this
     │  hooks (async, silent, always exit 0)
     ▼
  emit.sh ──► sessions/<id>.json ──► publish.py ──PUT──► private repo
     │                                (one API call)   (one file per session)
     └─ on SessionStart: sweep.py                            │
                                                        GET + ETag
                                                             ▼
                                              serve.py ──► dashboard ──► your phone
                                              (no clone, no state)
```

`publish.py` writes exactly one file — this session's — with a single
`PUT /repos/<you>/forge-state/contents/sessions/<id>.json`. There is no clone
anywhere: not on the machines that publish, not on the machine that displays.
One session owns one path, so an update needs nothing but that file's blob sha,
and two sessions never contend. History is kept, because every PUT is a commit.

The dashboard reads the same store live, with a conditional request. GitHub's
own words: *"Making a conditional request does not count against your primary
rate limit if a `304` response is returned"* — so polling hard is free, and the
page is current rather than current-as-of-the-last-sync. Only blobs whose sha
changed are fetched; everything else is served from what it already has.

## The three properties, each of them a test

1. **Silent.** The emitter writes zero bytes to stdout and stderr on every
   event. Claude Code shows a hook's stdout to the model on exactly three events
   (`SessionStart`, `UserPromptSubmit`, `UserPromptExpansion`); printing nothing
   means the session cannot observe this layer on any of them.
2. **Harmless.** It always exits 0 — on malformed input, no input, an
   unwritable state directory, a stripped environment. Exit 2 is a *blocking*
   error on several events. A gate must fail closed; a monitor must fail open,
   because a monitor that can stop a turn eventually will, at the worst moment.
3. **Session-keyed.** Nothing is stored per machine. `verify.sh` fails if a
   machine-keyed directory ever appears.

## What happens when a session dies

A closed laptop lid fires no `SessionEnd`, so a record would claim to be running
forever. There is no watchdog, because there is no daemon. Instead **the next
session to start sweeps**: the system repairs itself at the only moment the
repair matters.

The sweep is deliberately conservative. A session blocked on a permission prompt
emits nothing *precisely because it is waiting for you* — that is the most
important row on the dashboard, and hiding it would be the worst possible
outcome. So a stale record keeps its state and its reason and is only **flagged**;
the page shows it greyed with "not heard from since". Records are only deleted
once they have finished and gone quiet for three days.

## Setup

**Per project**, in a committed `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "forge": { "source": { "source": "github", "repo": "mde-pach/forge" } }
  },
  "enabledPlugins": { "forge-monitor@forge": true }
}
```

**Once**, the store — no personal access token needed:

```bash
gh auth login && gh auth setup-git    # points git's credential helper at gh
gh repo create <you>/forge-state --private
```

```jsonc
// ~/.local/state/forge-monitor/config.json
{
  "store": { "repo": "<you>/forge-state", "branch": "main" },
  "min_publish_seconds": 120,   // rate limit for non-urgent events
  "stale_minutes": 45,          // silence after which a record is flagged
  "forget_hours": 72            // when finished records are deleted
}
```

**To look at it**, from any machine that can reach the API:

```bash
uv run forge start                # http://127.0.0.1:7373, plus your tailnet URL
```

`serve.py` and `expose.sh` are not entry points; `forge start` is the only thing
that runs them. It prints a readiness report first — whether the store is
configured, whether a token was found, whether the store answered — because a
diagnostic you have to know about and remember to run is one nobody runs. That
report replaced a `forge doctor` command that nothing ever called.

`tailscale serve`, never `tailscale funnel`: serve reaches devices on your
tailnet, funnel publishes to the internet, and for session state that
distinction is the whole security model. Stopping `forge start` takes the
mapping down again.

## The dashboard

Waiting-on-you first, oldest demand at the top, because the thing that has been
waiting longest is the thing you most need to see. Then running, then recently
finished. Each row carries the project, the machine, the working directory, how
long, and a **copy resume command** button — this is a window, not a remote
control, so the least it can do is hand you `cd <cwd> && claude --resume <id>`
rather than a session id to retype.

## Known holes

- **Never tested against a real session, or a real store.** Every test uses
  payloads written by hand from documentation, and this sandbox gets a 403 from
  `api.github.com`, so neither the PUT nor the conditional GET has ever run
  against GitHub. If a field name or a response shape is wrong, the dashboard
  shows an empty waiting list forever and nothing fails loudly. This is the
  first thing to fix.
- **Cloud sessions run the plugin but cannot publish** — the container is
  isolated and discarded, and giving it a credential means giving the agent one.
  Undecided.
- **No notifications.** The dashboard answers "what is the state", never "come
  look now". `ntfy` from `publish.sh` is the cheap next step.
- **The statusline is opt-in.** A plugin's settings support only two keys, so
  `statusline.sh` cannot be installed by the plugin. Point your own `statusLine`
  at it for cost, context-window and rate-limit numbers.
