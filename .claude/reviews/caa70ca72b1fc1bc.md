# Review: PWA dashboard (forge-monitor), v3 — verifying the two prior fixes

## Summary
Both prior fixes are correctly implemented: `dataFirst()` in `sw.js` now falls back to
the cached snapshot on a non-2xx response, and `README.md`'s "Known holes" section now
acknowledges the Cache Storage privacy tradeoff and DATA_CACHE's manual versioning. One
process note: `sw.js` is untracked (`??`), not modified (`M`), so `git diff` produced no
output for it — I read the file directly instead. The changed-file set also includes two
files outside the expected list (`docs/how-to/monitor.md`, `src/forge/checks/orphans.py`).

## Findings

**Fix #1 (sw.js `dataFirst()` hardening) — correct.**
`git diff -- plugins/forge-monitor/dashboard/sw.js` produced no output because the file
is untracked (confirmed via `git status --short` showing `??` and `git ls-files`
returning nothing), not tracked-and-modified as the task background assumed. I read the
file in full instead. The relevant logic:

```js
async function dataFirst(request) {
  const key = new Request(new URL(request.url).pathname);
  try {
    const fresh = await fetch(request);
    if (fresh.ok) {
      const cache = await caches.open(DATA_CACHE);
      cache.put(key, fresh.clone());
      return fresh;
    }
    const cached = await caches.match(key);
    return cached || fresh;
  } catch (err) {
    const cached = await caches.match(key);
    if (cached) return cached;
    throw err;
  }
}
```

- Success path (`fresh.ok`): clones before caching, returns the original response —
  no double-read of the body, no missed `return`.
- Non-2xx path: falls back to `caches.match(key)`; returns the cached snapshot if one
  exists, otherwise returns the real (failing) `fresh` response so a genuine failure with
  nothing cached still surfaces rather than being swallowed.
- Real network failure (`catch`): unchanged — falls back to cache or rethrows.

This is exactly the requested hardening, with no control-flow bugs.

**Fix #2 (README privacy/versioning acknowledgment) — present and accurate.**
`git diff -- plugins/forge-monitor/README.md` shows a new "Known holes" bullet:
> "The offline fallback persists what used to live only in memory... a session's host
> and working directory existed in the browser only for the life of the tab, in a JS
> variable. Now the last snapshot is written to Cache Storage so it survives a reload
> with no network... it also means that data now sits on disk until the next successful
> fetch overwrites it, readable by anything with access to that origin's storage
> (devtools, a shared or lost device). Low risk, since the dashboard is reachable only
> over your own tailnet, but a real change... worth knowing about."

This covers the persistence-lifetime concern and names hostname/working-directory as the
sensitive fields; it does not explicitly say "session ids" by name, even though the
dashboard's snapshot data does include resume session ids (per the "copy resume command"
feature described elsewhere in the README). Minor nit, not a defect — the point (Cache
Storage extends exposure lifetime beyond in-memory) is made clearly and accurately.

A second new bullet explicitly covers DATA_CACHE's manual versioning:
> "Both caches are versioned by hand. `sw.js` bumps `SHELL_CACHE`'s and `DATA_CACHE`'s
> `-v1` suffix to invalidate old entries; a change that forgets to bump one still reaches
> clients... but one reload later than it should."

This matches the requested fix.

**Other findings — file list does not match expectations.**
`git status --short` shows:
```
 M docs/how-to/monitor.md
 M plugins/forge-monitor/README.md
 M plugins/forge-monitor/dashboard/index.html
 M plugins/forge-monitor/serve.py
 M src/forge/checks/orphans.py
?? plugins/forge-monitor/dashboard/icons/
?? plugins/forge-monitor/dashboard/manifest.webmanifest
?? plugins/forge-monitor/dashboard/sw.js
```
Two files outside the task's expected changed-file list are also modified:
- `docs/how-to/monitor.md` — adds a short paragraph about the dashboard being
  installable and working offline. Content-wise this is consistent with the PWA feature
  and looks like a reasonable, low-risk doc update (not deeply reviewed, per scope).
- `src/forge/checks/orphans.py` — adds `.claude/reviews/` to `SERVED_DIRS` (files found
  by fingerprint rather than named in prose), with a comment explaining review files are
  looked up by content-hash. This is unrelated to the PWA/service-worker work and appears
  to be a repo-process change (exempting the reviews directory from an orphan-file check),
  bundled into this diff rather than being part of the PWA changeset. Not reviewed in
  depth per task scope, but flagged since it's scope creep relative to the stated file
  list.

Neither of these two files affects the correctness of fix #1 or fix #2, but the actual
changed-file set is not the exact list given in the task.

## Verdict
APPROVE — both fixes are implemented correctly, with only a minor README nit (session
ids not named explicitly) and an out-of-scope-but-harmless pair of extra file changes
worth a human's awareness.
