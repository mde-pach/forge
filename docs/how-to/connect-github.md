# How to give Claude GitHub access for forge

## Primary: GitHub's official remote MCP server as a custom connector (one-time, all surfaces)

Durable, account-level, no tokens in chat. Once connected, every Claude surface (web, mobile, Cowork, Desktop) gets repo tools automatically. Verified working 2026-08-16.

1. **Create a GitHub OAuth App** (GitHub → Settings → Developer settings → OAuth Apps → New OAuth App). GitHub does not support automatic client registration, so Claude needs your own app:
   - Homepage URL: `https://claude.ai`
   - Authorization callback URL: `https://claude.ai/api/mcp/auth_callback` (exact — used by all Claude surfaces)
   - Register, copy the Client ID, generate and copy a Client Secret.
2. **Add the custom connector — from claude.ai in a browser, not the mobile app** (the mobile app can only browse the directory): claude.ai → Settings → Connectors → Add custom connector.
   - Name: `GitHub` — URL: `https://api.githubcopilot.com/mcp/x/repos`
     (`/x/repos` exposes only the repository toolset — create repo, read/write contents, branches — least privilege by URL; append `/readonly` for read-only surfaces)
   - Put the OAuth App's Client ID and Client Secret in the OAuth fields.
3. Connect → GitHub authorization page → authorize.
4. In a session, enable the connector in the chat's connector settings if it isn't already.

Notes: writes go through GitHub's API (`push_files` = one commit per call), so sessions mirror their local git commits one by one — history stays meaningful. Renames need `push_files` + `delete_file` (two commits).

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
