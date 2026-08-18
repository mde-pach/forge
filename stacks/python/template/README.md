# __PROJECT__

__DESCRIPTION__

```bash
uv sync                 # install (creates .venv and uv.lock)
uv run python -m __MODULE__
uv run pytest
docker compose up --build
```

Quality gates run automatically inside Claude Code sessions (see `.claude/`).
Run them by hand with `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy`.
