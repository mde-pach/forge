# How to build and run docs (the forge standard)

This is the standard docs pipeline for forge and for every project under it.

## The pattern

- **Markdown in the repo is the only source.** Kernel, contract, frictions, capability procedures live where they live; nothing is written twice.
- **The site is a generated projection.** `docs/.vitepress/assemble.mjs` copies canonical files into `docs/generated/` (gitignored) at build time; the site is built from `docs/` with VitePress. Editing anything under `generated/` or `dist/` is always wrong — edit the source and rebuild.
- **Diátaxis quadrants stay unmixed**: reference (kernel, contract, sources), explanation (`docs/explanation.md`), how-to guides (`docs/how-to/`). Tutorials appear when a real onboarding need does.

## Run locally

```
npm install
npm run docs:dev      # live-reload at localhost:5173
npm run docs:build    # static site → docs/.vitepress/dist
```

## Deploy

The Vercel project is linked to the GitHub repo: every push to `main` rebuilds and redeploys the site automatically (`vercel.json` pins build command and output directory — explicit over detection). A session with the Vercel connector can also deploy directly when needed.

## Applying the standard to a new project

Copy `package.json` docs scripts, `docs/.vitepress/` (config + assemble map adapted to that project's canonical files), and `vercel.json`; link the repo to a Vercel project once. Everything else follows.
