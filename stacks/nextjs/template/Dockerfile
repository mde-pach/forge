# syntax=docker/dockerfile:1
# Three stages, following vercel/next.js examples/with-docker.
# Requires `output: "standalone"` in next.config.ts.
#
# bun installs and builds; node runs. Next's standalone output ships a
# server.js meant for node, so the runtime stage stays node - and staying node
# keeps the final image free of a toolchain it never uses.
ARG BUN_VERSION=1.2-slim
ARG NODE_VERSION=22-slim

FROM oven/bun:${BUN_VERSION} AS deps
WORKDIR /app
COPY package.json bun.lock* ./
RUN --mount=type=cache,target=/root/.bun bun install --frozen-lockfile

FROM oven/bun:${BUN_VERSION} AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN bun run build

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
