# Parallax web (Next.js standalone). Runtime env: PARALLAX_API_URL, PARALLAX_API_TOKEN, PORT.
# No secrets at build time; the API types are generated ahead of time and committed.
FROM node:22.23.3-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22.23.3-bookworm-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22.23.3-bookworm-slim AS run
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    NODE_OPTIONS=--max-old-space-size=384
RUN groupadd --system --gid 1001 parallax && useradd --system --uid 1001 --gid parallax --no-create-home parallax
COPY --from=build --chown=parallax:parallax /app/.next/standalone ./
COPY --from=build --chown=parallax:parallax /app/.next/static ./.next/static
COPY --from=build --chown=parallax:parallax /app/public ./public
USER parallax
EXPOSE 3000
CMD ["node", "server.js"]
