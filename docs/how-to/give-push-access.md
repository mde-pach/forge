# How to give a session push access to the forge repo

Cloud sessions are ephemeral containers: credentials do not survive container reclamation. Until a durable GitHub connector exists (none in the registry as of 2026-08), push access is granted per session.

## One-time (you)

1. Create the private repo on GitHub (e.g. `forge`), empty, no README.
2. Create a fine-grained personal access token: GitHub → Settings → Developer settings → Fine-grained tokens → Generate.
   - Repository access: **only the forge repo**
   - Permissions: **Contents: Read and write**. Nothing else.
   - Expiration: your call; shorter = safer, more re-issuing.

## Per session (you)

Paste the token in chat with the repo URL, e.g.: `push access: https://github.com/<you>/forge  token: github_pat_...`

## Per session (Claude)

```
cd forge
git remote add origin https://x-access-token:<TOKEN>@github.com/<you>/forge.git 2>/dev/null \
  || git remote set-url origin https://x-access-token:<TOKEN>@github.com/<you>/forge.git
git push -u origin main
git remote set-url origin https://github.com/<you>/forge.git   # scrub token from config after push
```

Rules: the token never enters any committed file, any report, or any projection. Scrub the remote URL after pushing. If a push fails with 403, say so and stop — do not retry with broader guesses.
