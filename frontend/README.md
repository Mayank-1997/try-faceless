# AI Video Studio — Frontend Monorepo

## Architecture Overview

This is the frontend monorepo for the AI Video Studio SaaS platform, built with Turborepo and pnpm workspaces.

## Tech Stack

- **Monorepo**: Turborepo + pnpm workspaces
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript 5.5 (strict mode)
- **Styling**: Tailwind CSS 3.4 with CSS variable-based theming
- **State Management**: Zustand (client state) + TanStack Query v5 (server state)
- **API Layer**: Axios with interceptors, token refresh, retry logic
- **Realtime**: Socket.IO client
- **Icons**: Lucide React (centralized exports)
- **Animations**: Framer Motion

## Package Structure

```
frontend/
├── apps/
│   └── web/                      # Next.js application (App Router)
│       ├── src/app/              # App router pages and layouts
│       ├── next.config.js
│       ├── tailwind.config.ts
│       └── tsconfig.json
├── packages/
│   ├── shared-types/             # TypeScript types, DTOs, enums
│   ├── shared-utils/             # Utility functions (date, format, string, validate, file, cn)
│   ├── shared-hooks/             # Reusable React hooks
│   ├── theme/                    # Design tokens, CSS variables, theme helpers
│   ├── icons/                    # Centralized Lucide icon exports
│   ├── design-system/            # UI component library
│   │   ├── src/primitives/       # Button, Input, Card, Dialog, Tabs, etc.
│   │   ├── src/business/         # ProjectCard, UserCard, ApiKeyCard, etc.
│   │   └── src/lib/              # cn utility
│   ├── platform-sdk/             # API client and SDK modules
│   │   ├── src/api-client.ts     # Axios wrapper with interceptors
│   │   ├── src/sdk.ts            # Main SDK class
│   │   ├── src/modules/          # Auth, Users, ApiKeys, Sessions SDK
│   │   └── src/hooks/            # TanStack Query hooks
│   ├── platform-kernel/          # Platform infrastructure
│   │   ├── src/providers/        # PlatformProvider, ErrorBoundary, ThemeProvider, QueryProvider
│   │   ├── src/stores/           # Zustand auth store
│   │   ├── src/feature-registry.ts
│   │   ├── src/plugin-manager.ts
│   │   ├── src/command-palette.tsx
│   │   └── src/realtime.ts       # WebSocket provider
│   ├── eslint-config/            # Shared ESLint configs
│   └── tsconfig/                 # Shared TypeScript configs
├── package.json                  # Root workspace config
├── turbo.json                    # Turborepo pipeline
├── pnpm-workspace.yaml           # pnpm workspace config
└── tsconfig.json                 # Root TypeScript config
```

## Platform Kernel Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    PlatformProvider                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │ ErrorBoundary│  │ ThemeProvider │  │ QueryProvider   │ │
│  └─────────────┘  └──────────────┘  └─────────────────┘ │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                    ToastProvider                     │ │
│  └─────────────────────────────────────────────────────┘ │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ AuthStore │  │ FeatureReg   │  │ PluginManager    │  │
│  │ (Zustand) │  │              │  │                  │  │
│  └──────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ CommandPalette   │  │ RealtimeProvider (Socket.IO) │ │
│  └──────────────────┘  └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## Platform SDK Architecture

```
┌─────────────────────────────────────────────────┐
│                  PlatformSDK                     │
│  ┌──────────────────────────────────────────┐   │
│  │              ApiClient                    │   │
│  │  ┌─────────────┐  ┌──────────────────┐   │   │
│  │  │ Request     │  │ Response         │   │   │
│  │  │ Interceptor │  │ Interceptor      │   │   │
│  │  │ (auth token)│  │ (refresh, retry) │   │   │
│  │  └─────────────┘  └──────────────────┘   │   │
│  └──────────────────────────────────────────┘   │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐ │
│  │ Auth   │ │ Users  │ │ ApiKeys  │ │Sessions│ │
│  │ SDK    │ │ SDK    │ │ SDK      │ │ SDK    │ │
│  └────────┘ └────────┘ └──────────┘ └────────┘ │
│  ┌──────────────────────────────────────────┐   │
│  │         TanStack Query Hooks              │   │
│  │  useLogin | useCurrentUser | useApiKeys   │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Design System Components

### Primitives
- **Button** — 6 variants (default, secondary, outline, ghost, destructive, link), 4 sizes
- **Input** — Text input with theme-aware styling
- **Textarea** — Multi-line text input
- **Card** — Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter
- **Badge** — 7 variants (default, secondary, success, warning, error, info, outline)
- **Avatar** — Image with fallback initials, 3 sizes
- **Skeleton** — Loading placeholder with pulse animation
- **Progress** — Progress bar with ARIA support
- **Switch** — Toggle switch
- **Checkbox** — Checkbox with check icon
- **Dialog** — Modal dialog with backdrop, ESC to close
- **Tabs** — Controlled/uncontrolled tabs with context
- **Select** — Native select with theme styling
- **Tooltip** — Hover tooltip with 4 positions
- **Table** — Table, TableHeader, TableBody, TableRow, TableHead, TableCell
- **Drawer** — Side drawer (left, right, top, bottom)
- **Toast** — ToastProvider + useToast hook, 5 variants
- **Popover** — Click-triggered popover with 3 alignments
- **States** — EmptyState, ErrorState, LoadingState

### Business Components
- **ProjectCard** — Video project card with status, progress, thumbnail
- **GenerationProgressCard** — AI generation progress with step tracking
- **UserCard** — User display card with avatar, role, status
- **ApiKeyCard** — API key card with masked key, scopes, revoke action

## Getting Started

### Prerequisites
- Node.js 20+
- pnpm 9+

### Installation
```bash
cd frontend
pnpm install
```

### Development
```bash
pnpm dev
```

### Build
```bash
pnpm build
```

### Environment Variables
Copy `apps/web/.env.example` to `apps/web/.env.local` and configure:
- `NEXT_PUBLIC_API_BASE_URL` — Backend API base URL
- `NEXT_PUBLIC_WS_URL` — WebSocket URL
- `NEXT_PUBLIC_APP_VERSION` — App version
- `NEXT_PUBLIC_ENV` — Environment (development, staging, production)

## Coding Standards

- **TypeScript**: Strict mode, no `any` types, explicit return types
- **ESLint**: Shared config across all packages
- **Prettier**: Consistent formatting
- **Naming**: PascalCase for components, camelCase for functions/variables, kebab-case for files
- **Imports**: Use workspace references (`@ai-video-studio/*`)
- **Testing**: Tests should be co-located with source files

## Contribution Guide

1. Create a feature branch from `main`
2. Make changes following coding standards
3. Ensure `pnpm lint` and `pnpm type-check` pass
4. Write tests for new features
5. Submit a pull request with a clear description

## Phase 1 Status

All foundational packages are complete:
- [x] shared-types
- [x] shared-utils
- [x] shared-hooks
- [x] theme
- [x] icons
- [x] design-system
- [x] platform-sdk
- [x] platform-kernel
- [x] web app (Next.js App Router)
- [x] eslint-config
- [x] tsconfig

**Awaiting approval to proceed to Frontend Phase 2.**
