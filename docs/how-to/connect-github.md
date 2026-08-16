# How to give Claude GitHub access for forge

## Primary: GitHub's official remote MCP server as a custom connector (one-time, all surfaces)

Durable, account-level, no tokens in chat. Works on Claude web/mobile, Cowork, and Desktop; sessions get repo tools automatically.

1. Claude app → Settings → Connectors → **Add custom connector**
2. Name: `GitHub` — URL: `https://api.githubcopilot.com/mcp/x/repos`
   (the `/x/repos` path exposes only the repository toolset — create repo, read/write contents, branches — least privilege by URL; append `/readonly` for read-only surfaces)
3. Connect → OAuth sign-in to GitHub → authorize.
4. In a session, enable the connector in the chat's connector settings if it isn't already.

Notes: writes go through GitHub's API (`push_files` = one commit per call), so sessions mirror their local git commits one by one — history stays meaningful. If OAuth is refused (some accounts route this through Copilot access), fall back to the PAT method below.

## Fallback: per-session fine-grained PAT (raw git push)

1. Create the private repo on GitHub if it doesn't exist.
2. Fine-grained token: repository access = only the forge repo; permissions = Contents: read/write; nothing else.
3. Paste token + repo URL in chat. Claude then:

```
git remote set-url origin https://x-access-token:<TOKEN>@github.com/<you>/forge.git
git push -u origin main
git remote set-url origin https://github.com/<you>/forge.git   # scrub token after push
```

Rules (both methods): credentials never enter a committed file, a report, or a projection; on a 403, stop and say so — never retry with broader guesses.
