# Give Claude GitHub access

## Custom connector (all surfaces, one-time)

1. Create a GitHub OAuth App (Settings → Developer settings → OAuth Apps):
   homepage `https://claude.ai`, callback `https://claude.ai/api/mcp/auth_callback`.
   Copy the Client ID and a Client Secret.
2. In claude.ai (browser, not the mobile app): Settings → Connectors → Add custom connector.
   Name `GitHub`, URL `https://api.githubcopilot.com/mcp/x/all`. Use `/x/repos`
   for contents only, or append `/readonly`. Paste the Client ID and Secret.
3. Connect and authorise. Enable the connector in a session's connector settings if needed.

Writes go through the API: `push_files` is one commit per call; a rename is
`push_files` plus `delete_file`.

## Fallback: per-session fine-grained token

1. Create the private repository.
2. Token scope: that repository only, Contents read/write, nothing else.
3. Paste token and repository URL in chat. Claude runs:

```
git remote set-url origin https://x-access-token:<TOKEN>@github.com/<you>/forge.git
git push -u origin main
git remote set-url origin https://github.com/<you>/forge.git
```

Credentials never enter a committed file, a report or a projection. On a 403,
stop and say so; never retry with broader guesses.
