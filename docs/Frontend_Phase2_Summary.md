# Frontend Phase 2 — Workspace Experience & Project Management

## Overview

Phase 2 implements the workspace shell, project CRUD operations, navigation, command palette integration, and authentication pages. All project operations are integrated with the backend API through the platform SDK and React Query hooks.

## Deliverables

### 1. Shared Types (shared-types)
- **`business-dto.ts`**: DTOs for Project, Workflow, Research, Script, Storyboard, Scene, Asset, GenerationJob, PromptExecution, and Analytics — mirroring backend Pydantic models.
- **Enums**: `ContentType`, `VideoStyle`, `WorkflowStep`, `WorkflowStatus` already defined in `enums.ts`.

### 2. Platform SDK (platform-sdk)
- **`modules/projects.ts`**: `ProjectsSDK` class with methods:
  - `list(params?)` — GET `/projects` with optional status/content_type/offset/limit filters
  - `getById(id)` — GET `/projects/{id}`
  - `create(data)` — POST `/projects`
  - `update(id, data)` — PATCH `/projects/{id}`
  - `delete(id)` — DELETE `/projects/{id}`
  - `getWorkflow(id)` — GET `/projects/{id}/workflow`
  - `startWorkflow(id)` — POST `/projects/{id}/workflow/start`
  - `cancelWorkflow(id)` — POST `/projects/{id}/workflow/cancel`
- **`hooks/project-hooks.ts`**: React Query hooks:
  - `useProjects(params?)` — list query with auto invalidation
  - `useProject(id)` — detail query
  - `useCreateProject()` — create mutation, invalidates list
  - `useUpdateProject()` — update mutation, updates detail cache + invalidates list
  - `useDeleteProject()` — delete mutation, invalidates list
  - `useProjectWorkflow(id)` — workflow query
  - `useStartWorkflow()` — start workflow mutation
  - `useCancelWorkflow()` — cancel workflow mutation
  - `projectKeys` — query key factory for cache management

### 3. Workspace Shell Components
- **`Sidebar.tsx`**: Collapsible navigation with Dashboard, Projects links + New Project button
- **`TopNav.tsx`**: Search trigger (⌘K), theme toggle, notifications, user avatar, logout
- **`InspectorPanel.tsx`**: Collapsible right panel for contextual information
- **`StatusBar.tsx`**: Bottom bar showing project name, workflow step, realtime connection status
- **`WorkspaceShell.tsx`**: Integrates all shell components + CommandPalette

### 4. Pages
- **`/` (Home)**: Redirects to `/dashboard` or `/login` based on auth state
- **`/login`**: Email/password login form with branding
- **`/register`**: Registration form with first_name, last_name, username, email, password
- **`/dashboard`**: Stats cards (total, in-progress, completed, failed) + recent projects grid
- **`/projects`**: Project list with search, status filter, delete confirmation dialog
- **`/projects/new`**: 3-step wizard (Content Type → Details → Review) with ContentType and VideoStyle selection
- **`/projects/[id]`**: Project detail with metadata cards, workflow progress visualization (13 steps), edit/delete dialogs, start/cancel workflow actions
- **`/settings`**: Profile info, theme selector, notification placeholder, security info

### 5. Command Palette Integration
- **`useWorkspaceCommands.ts`**: Registers navigation commands (Dashboard, Projects, New Project, Settings), theme toggle, and logout
- Commands are registered on workspace layout mount and unregistered on unmount
- ⌘K / Ctrl+K opens the palette globally

### 6. Icons
- Added `LayoutDashboard`, `FolderKanban`, `Pencil`, `Trash2`, `BookOpen`, `GraduationCap`, `Tag` to the icons package

## Architecture Decisions

- **No direct API calls from pages**: All data operations go through platform SDK hooks
- **React Query for server state**: Mutations invalidate relevant query keys automatically
- **Zustand for auth state**: `useAuthStore` with `setUser`, `setTokens`, `clearAuth` methods
- **Design system components**: All UI uses `@ai-video-studio/design-system` primitives
- **CSS variable theming**: All colors use `var(--*)` pattern for light/dark mode support
- **Type safety**: All DTOs and enums imported from `@ai-video-studio/shared-types`

## File Structure

```
apps/web/src/
├── app/
│   ├── page.tsx                          # Home redirect
│   ├── login/page.tsx                    # Login page
│   ├── register/page.tsx                 # Register page
│   └── (workspace)/
│       ├── layout.tsx                    # Auth guard + WorkspaceShell
│       ├── dashboard/page.tsx            # Dashboard
│       ├── projects/
│       │   ├── page.tsx                  # Project list
│       │   ├── new/page.tsx              # Creation wizard
│       │   └── [id]/page.tsx             # Project detail
│       └── settings/page.tsx             # Settings
├── components/workspace/
│   ├── WorkspaceShell.tsx
│   ├── Sidebar.tsx
│   ├── TopNav.tsx
│   ├── InspectorPanel.tsx
│   └── StatusBar.tsx
└── hooks/
    └── useWorkspaceCommands.ts           # Command palette registrations
```

## Testing

- **`project-hooks.test.ts`**: Unit tests for all project hooks and SDK methods, verifying correct query keys, mutation behavior, and SDK call patterns.

## What's NOT Included (Phase 2 Scope)

- AI content creation (Phase 3)
- Video production/rendering (Phase 4)
- Analytics, billing, publishing (Phase 5)
- Real-time workflow updates via WebSocket (planned for Phase 3)
