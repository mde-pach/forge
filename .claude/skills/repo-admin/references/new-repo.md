# Creating a repository, from nothing to green CI

The whole sequence is session-doable with the `/x/repos` toolset. It is written
out because every step here has failed at least once when improvised.

## 0 · Approval first

Creating a repository is outward-facing and hard to undo, and **visibility is
the decision, not a default**. A repo was once created public without being
asked. The approval must name three things explicitly:

- the **name** and the **owner** (personal account or org)
- **public or private**
- the **licence** (or explicitly none)

If any of the three is missing from the approval, ask for it. Do not infer
"public" from the fact that other repos are public.

## 1 · Scaffold locally, and verify, before anything is created

```bash
bash .claude/skills/scaffold/scaffold.sh python /path/to/name "What it does"
```

Do not proceed unless the output says `verifier : PASS`. Creating the repo
first and fixing it afterwards puts broken commits in a public history.

## 2 · Create the repository

`create_repository` — `name`, `description`, `private` (from the approval),
`autoInit: false`.

`autoInit: true` creates a commit you did not write, and the first real push
then needs a merge or a force. Start empty.

## 3 · Push the tree

`push_files` — one call, all files, `branch: "main"`, a real commit message.

Three things this API does that a `git push` does not:

- **`git push` is blocked by the sandbox proxy.** This is the only route.
- **File modes are lost**: everything lands as `100644`. Hook scripts arrive
  non-executable. A hook that cannot execute exits 127, and Claude Code treats
  any exit code other than 0 or 2 as **non-blocking** — the gate is off while
  the settings file still says it is on. Forge scaffolds are immune because
  `settings.json` invokes them as `bash <script>`, but check this on any repo
  that did not come from a scaffold.
- **Generated files must not be sent**: `uv.lock` / `package-lock.json` are
  produced by the scaffold and are safe to push, but nothing under `.venv/`,
  `node_modules/`, `.next/` or `dist/` ever goes through this API.

## 4 · Prove the push, do not assume it

- `get_file_contents` on two or three files, including one hook, and compare
  the blob SHA to the local `git hash-object` output.
- `list_commits` — the commit exists, with the message you wrote.

## 5 · Let CI be the real proof

The scaffold ships `.github/workflows/ci.yml`, which runs the *same* `gate.sh`
the local hook runs, plus a docker build. Poll the run:

```
GET https://api.github.com/repos/<owner>/<repo>/actions/runs
```

Public repos need no token for this and no extra connector toolset. Red CI on
the first push means the scaffold's promise was not kept — report it and open a
friction entry, do not retry blindly.

## 6 · What still needs a human, and why

| Operation | Reachable? |
|---|---|
| create repo, push, read CI | yes — `/x/repos` + the public runs API |
| open an issue, comment | **no** — needs the connector URL switched to `/x/all` |
| branch protection / rulesets | **no** — needs `Administration: write`, i.e. the rung-3 `ADMIN_TOKEN` reconciler |
| first-time Pages enablement | **no** — GitHub admin-gates Pages *creation*; one click, Settings → Pages → Source: GitHub Actions |

Rung 3 (`admin.yml` driven by pushing a desired-state file, using a
fine-grained PAT stored as the `ADMIN_TOKEN` repo secret) removes rows 3 and 4.
Its trigger has now fired more than twice. That is the signal to build it, not
to escalate a fourth time.

## Never

- Put a token in a git remote, a committed file, a report, or a projection.
- Retry a 403 with a broader scope guess. Stop, say which operation was refused,
  and which rung would reach it.
