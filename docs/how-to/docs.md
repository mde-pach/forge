# How to build and run docs (the forge standard)

This is the standard docs pipeline for forge and for every project under it.

## The pattern

- **Markdown in the repo is the only source.** Kernel, contract, capability procedures live where they live; nothing is written twice.
- **The site is a generated projection.** `docs/.vitepress/assemble.mjs` copies canonical files into `docs/generated/` (gitignored) at build time; the site is built from `docs/` with VitePress. Editing anything under `generated/` or `dist/` is always wrong — edit the source and rebuild.
- **Diátaxis quadrants stay unmixed**: reference (kernel, contract, sources), explanation (`docs/explanation.md`), how-to guides (`docs/how-to/`). Tutorials appear when a real onboarding need does.

## Run locally

```
npm install
uv run forge docs --dev     # live-reload at localhost:5173
uv run forge docs           # static site → docs/.vitepress/dist
uv run forge docs --check   # fail if the generated pages are stale
```

## Deploy — GitHub Pages

`.github/workflows/docs.yml` builds the site on every push to `main` and deploys it via GitHub Pages (actions/deploy-pages). One-time setup per repo: Settings → Pages → Source: **GitHub Actions**. The site URL is `https://<owner>.github.io/<repo>/` (the VitePress `base` option must match `/<repo>/`).

Note: on the GitHub Free plan, Pages only works on public repositories; a private repo needs GitHub Pro. Fallback if Actions is unavailable: build locally and push `docs/.vitepress/dist` to a `gh-pages` branch, source it in Pages settings.

## Applying the standard to a new project

Copy `package.json` docs scripts, `docs/.vitepress/` (config with `base` set to the repo name + assemble map adapted to that project's canonical files), and `.github/workflows/docs.yml`; enable Pages (Source: GitHub Actions) once. Everything else follows.
