FROM node:22-alpine

RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /app

# Copy only package.json files for dependency resolution (cached unless deps change)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY packages/eslint-config/package.json ./packages/eslint-config/package.json
COPY packages/tsconfig/package.json ./packages/tsconfig/package.json
COPY packages/shared-types/package.json ./packages/shared-types/package.json
COPY packages/shared-utils/package.json ./packages/shared-utils/package.json
COPY packages/shared-hooks/package.json ./packages/shared-hooks/package.json
COPY packages/theme/package.json ./packages/theme/package.json
COPY packages/icons/package.json ./packages/icons/package.json
COPY packages/design-system/package.json ./packages/design-system/package.json
COPY packages/platform-sdk/package.json ./packages/platform-sdk/package.json
COPY packages/platform-kernel/package.json ./packages/platform-kernel/package.json
COPY apps/web/package.json ./apps/web/package.json

RUN pnpm install --frozen-lockfile

# Now copy all source code (this layer changes often but deps are already installed)
COPY . .

WORKDIR /app/apps/web

EXPOSE 3000

CMD ["npx", "next", "dev", "--port", "3000", "--hostname", "0.0.0.0"]
