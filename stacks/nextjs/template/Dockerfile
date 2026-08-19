# syntax=docker/dockerfile:1
# Three stages, following vercel/next.js examples/with-docker.
# Requires `output: "standalone"` in next.config.ts.
#
# bun installs, node builds, node runs. See the builder stage for why the
# middle one is not bun.
ARG BUN_VERSION=1.2-slim
ARG NODE_VERSION=22-slim

FROM oven/bun:${BUN_VERSION} AS deps
WORKDIR /app
COPY package.json bun.lock* ./
RUN --mount=type=cache,target=/root/.bun bun install --frozen-lockfile

# bun installs; NODE builds. Next 16's production build cannot run under Bun:
# it spawns worker_threads with options Bun has not implemented, then fails
# loading a compiled CommonJS runtime ("Expected CommonJS module to have a
# function wrapper"). Compilation and TypeScript both succeed; it dies in page
# data collection. On a developer machine `bun run build` works because node is
# on PATH and next's shebang wins - which is exactly why only the container
# caught this.
FROM node:${NODE_VERSION} AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN ./node_modules/.bin/next build

FROM node:${NODE_VERSION} AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME="0.0.0.0" NEXT_TELEMETRY_DISABLED=1
COPY --from=builder --chown=node:node /app/public ./public
RUN mkdir .next && chown node:node .next
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
