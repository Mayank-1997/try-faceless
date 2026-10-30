'use client'

import Link from 'next/link'
import { useProjects } from '@ai-video-studio/platform-sdk'
import { Card, CardContent, CardHeader, CardTitle, Button, Badge, Skeleton } from '@ai-video-studio/design-system'
import { Plus, FolderKanban, Clock, CheckCircle2, AlertCircle, BarChart3, CreditCard, Settings, Shield } from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'

const statusBadgeVariant: Record<string, 'default' | 'secondary' | 'success' | 'warning' | 'error' | 'info' | 'outline'> = {
  draft: 'secondary',
  researching: 'info',
  scripting: 'info',
  planning: 'info',
  generating: 'warning',
  rendering: 'warning',
  publishing: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'outline',
}

export default function DashboardPage() {
  const { data, isLoading } = useProjects({ limit: 6 })

  const projects = data?.items ?? []
  const total = data?.total ?? 0

  const stats = [
    { label: 'Total Projects', value: total, icon: FolderKanban, color: 'text-[var(--brand-default)]' },
    { label: 'In Progress', value: projects.filter((p) => ['researching', 'scripting', 'planning', 'generating', 'rendering', 'publishing'].includes(p.status)).length, icon: Clock, color: 'text-[var(--status-warning)]' },
    { label: 'Completed', value: projects.filter((p) => p.status === 'completed').length, icon: CheckCircle2, color: 'text-[var(--status-success)]' },
    { label: 'Failed', value: projects.filter((p) => p.status === 'failed').length, icon: AlertCircle, color: 'text-[var(--status-error)]' },
  ]

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--fg-default)]">Dashboard</h1>
          <p className="text-sm text-[var(--fg-muted)]">Overview of your video projects</p>
        </div>
        <Link href="/projects/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Project
          </Button>
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="flex items-center gap-3 p-4">
              <div className={`rounded-lg bg-[var(--bg-surface-hover)] p-2.5 ${stat.color}`}>
                <stat.icon className="h-5 w-5" />
              </div>
              <div>
                <div className="text-2xl font-bold text-[var(--fg-default)]">{stat.value}</div>
                <div className="text-xs text-[var(--fg-muted)]">{stat.label}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Link href="/analytics">
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex items-center gap-2 p-3">
              <BarChart3 className="h-4 w-4 text-[var(--brand-default)]" />
              <span className="text-sm font-medium text-[var(--fg-default)]">Analytics</span>
            </CardContent>
          </Card>
        </Link>
        <Link href="/billing">
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex items-center gap-2 p-3">
              <CreditCard className="h-4 w-4 text-[var(--brand-default)]" />
              <span className="text-sm font-medium text-[var(--fg-default)]">Billing</span>
            </CardContent>
          </Card>
        </Link>
        <Link href="/settings">
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex items-center gap-2 p-3">
              <Settings className="h-4 w-4 text-[var(--brand-default)]" />
              <span className="text-sm font-medium text-[var(--fg-default)]">Settings</span>
            </CardContent>
          </Card>
        </Link>
        <Link href="/admin">
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex items-center gap-2 p-3">
              <Shield className="h-4 w-4 text-[var(--brand-default)]" />
              <span className="text-sm font-medium text-[var(--fg-default)]">Admin</span>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Recent Projects */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[var(--fg-default)]">Recent Projects</h2>
          <Link href="/projects">
            <Button variant="ghost" size="sm">View All</Button>
          </Link>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-4 w-32" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="mb-2 h-3 w-full" />
                  <Skeleton className="h-3 w-2/3" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : projects.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FolderKanban className="mb-3 h-10 w-10 text-[var(--fg-muted)]" />
              <p className="text-sm text-[var(--fg-muted)]">No projects yet. Create your first project to get started.</p>
              <Link href="/projects/new" className="mt-4">
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Project
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Link key={project.id} href={`/projects/${project.id}`}>
                <Card className="transition-shadow hover:shadow-md">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="truncate text-base">{project.title}</CardTitle>
                      <Badge variant={statusBadgeVariant[project.status] ?? 'default'}>
                        {project.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="mb-2 line-clamp-2 text-sm text-[var(--fg-muted)]">
                      {project.description || 'No description'}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-[var(--fg-muted)]">
                      <span>{project.content_type}</span>
                      <span>•</span>
                      <span>{formatRelativeTime(project.created_at)}</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
