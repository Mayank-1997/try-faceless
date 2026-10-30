'use client'

import Link from 'next/link'
import { useState } from 'react'
import { useProjects, useDeleteProject } from '@ai-video-studio/platform-sdk'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
  Input,
  Select,
  Dialog,
  Skeleton,
  EmptyState,
} from '@ai-video-studio/design-system'
import { Plus, Search, Trash2, FolderKanban, Pencil } from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import { useToast } from '@ai-video-studio/design-system'
import type { ProjectResponse } from '@ai-video-studio/shared-types'

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

export default function ProjectsPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<ProjectResponse | null>(null)
  const { addToast } = useToast()

  const { data, isLoading } = useProjects({
    status: statusFilter || undefined,
    limit: 50,
  })
  const deleteMutation = useDeleteProject({
    onSuccess: () => {
      addToast({ title: 'Project deleted', variant: 'success' })
      setDeleteTarget(null)
    },
    onError: (err) => {
      addToast({ title: 'Failed to delete project', description: err.message, variant: 'error' })
    },
  })

  const projects = data?.items ?? []
  const filtered = search
    ? projects.filter((p) => p.title.toLowerCase().includes(search.toLowerCase()))
    : projects

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--fg-default)]">Projects</h1>
          <p className="text-sm text-[var(--fg-muted)]">Manage your video projects</p>
        </div>
        <Link href="/projects/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Project
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--fg-muted)]" />
          <Input
            placeholder="Search projects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="w-40"
        >
          <option value="">All Status</option>
          <option value="draft">Draft</option>
          <option value="researching">Researching</option>
          <option value="scripting">Scripting</option>
          <option value="generating">Generating</option>
          <option value="rendering">Rendering</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </Select>
      </div>

      {/* Project Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
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
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={FolderKanban}
          title="No projects found"
          description="Create a new project to get started with AI video generation."
          action={
            <Link href="/projects/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Project
              </Button>
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((project) => (
            <Card key={project.id} className="transition-shadow hover:shadow-md">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <Link href={`/projects/${project.id}`}>
                    <CardTitle className="truncate text-base hover:text-[var(--brand-default)]">
                      {project.title}
                    </CardTitle>
                  </Link>
                  <Badge variant={statusBadgeVariant[project.status] ?? 'default'}>
                    {project.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="mb-3 line-clamp-2 text-sm text-[var(--fg-muted)]">
                  {project.description || 'No description'}
                </p>
                <div className="mb-3 flex flex-wrap gap-1">
                  {project.tags.slice(0, 3).map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--fg-muted)]">
                    {formatRelativeTime(project.created_at)}
                  </span>
                  <div className="flex gap-1">
                    <Link href={`/projects/${project.id}`}>
                      <Button variant="ghost" size="icon" className="h-7 w-7">
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                    </Link>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-[var(--status-error)] hover:text-[var(--status-error)]"
                      onClick={() => setDeleteTarget(project)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete Project">
        <p className="text-sm text-[var(--fg-muted)]">
          Are you sure you want to delete &quot;{deleteTarget?.title}&quot;? This action cannot be undone.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={() => setDeleteTarget(null)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  )
}
