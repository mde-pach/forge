# syntax=docker/dockerfile:1
# Multi-stage, following astral-sh/uv-docker-example. The builder and runtime
# base MUST stay on the same Python minor version - the venv hardcodes the
# interpreter path.
ARG PYTHON_VERSION=3.13

FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 UV_PYTHON_DOWNLOADS=0
WORKDIR /app
# Dependencies resolve in their own cached layer, before any source is copied.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked

FROM python:${PYTHON_VERSION}-slim-trixie
RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot
COPY --from=builder --chown=nonroot:nonroot /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER nonroot
WORKDIR /app
CMD ["python", "-m", "__MODULE__"]
