# Frontend: React Router 7 SSR app served by @react-router/serve on port 3000.
# Dependencies are managed with pnpm (pnpm-lock.yaml, lockfileVersion 9).
FROM node:24-alpine AS base
RUN npm install -g pnpm@10
WORKDIR /app

FROM base AS development-dependencies-env
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM base AS production-dependencies-env
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --prod

FROM base AS build-env
COPY . .
COPY --from=development-dependencies-env /app/node_modules ./node_modules
RUN pnpm run build

FROM base
COPY package.json ./
COPY --from=production-dependencies-env /app/node_modules ./node_modules
COPY --from=build-env /app/build ./build

EXPOSE 3000

CMD ["pnpm", "run", "start"]
