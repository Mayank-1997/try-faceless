'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useGenerationJobs, useProjectWorkflow } from '@ai-video-studio/platform-sdk'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Button,
  Badge,
  Skeleton,
  EmptyState,
  Progress,
} from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import { realtimeProvider } from '@ai-video-studio/platform-kernel'
import {
  ArrowLeft,
  Cpu,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Zap,
  AlertCircle,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import type { GenerationJobResponse } from '@ai-video-studio/shared-types'

const jobStatusConfig: Record<string, { variant: 'default' | 'secondary' | 'success' | 'warning' | 'error'; icon: typeof Clock; label: string }> = {
  queued: { variant: 'secondary', icon: Clock, label: 'Queued' },
  running: { variant: 'warning', icon: Loader2, label: 'Running' },
  completed: { variant: 'success', icon: CheckCircle2, label: 'Completed' },
  failed: { variant: 'error', icon: XCircle, label: 'Failed' },
  cancelled: { variant: 'secondary', icon: XCircle, label: 'Cancelled' },
  paused: { variant: 'secondary', icon: Clock, label: 'Paused' },
}

export default function GenerationPage() {
  const params = useParams()
  const projectId = params.id as string
  const { addToast } = useToast()
  const [realtimeJobs, setRealtimeJobs] = useState<Record<string, Partial<GenerationJobResponse>>>({})

  const { data: jobs, isLoading, error, refetch } = useGenerationJobs(projectId)
  const { data: workflow } = useProjectWorkflow(projectId)

  // Subscribe to realtime job updates
  useEffect(() => {
    const unsubscribe = realtimeProvider.on('job:status', (data: Record<string, unknown>) => {
      if (data.project_id === projectId) {
        setRealtimeJobs((prev) => ({
          ...prev,
          [data.id as string]: { status: data.status as string },
        }))
        if (data.status === 'completed') {
          addToast({ title: `Job ${data.id} completed`, variant: 'success' })
        } else if (data.status === 'failed') {
          addToast({ title: `Job ${data.id} failed`, variant: 'error' })
        }
        refetch()
      }
    })

    return unsubscribe
  }, [projectId, addToast, refetch])

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <Link href={`/projects/${projectId}`} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--fg-muted)] hover:text-[var(--fg-default)]">
          <ArrowLeft className="h-4 w-4" />
          Back to project
        </Link>
        <EmptyState
          icon={<AlertCircle className="h-12 w-12" />}
          title="Failed to load generation jobs"
          description="There was an error loading the generation dashboard."
        />
      </div>
    )
  }

  const allJobs = jobs ?? []
  const queuedJobs = allJobs.filter((j) => (realtimeJobs[j.id]?.status ?? j.status) === 'queued')
  const runningJobs = allJobs.filter((j) => (realtimeJobs[j.id]?.status ?? j.status) === 'running')
  const completedJobs = allJobs.filter((j) => (realtimeJobs[j.id]?.status ?? j.status) === 'completed')
  const failedJobs = allJobs.filter((j) => (realtimeJobs[j.id]?.status ?? j.status) === 'failed')

  const totalProgress = allJobs.length > 0
    ? (completedJobs.length / allJobs.length) * 100
    : 0

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/projects/${projectId}`}>
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-xl font-bold text-[var(--fg-default)]">Generation Dashboard</h1>
            <p className="text-sm text-[var(--fg-muted)]">
              {allJobs.length} jobs · {completedJobs.length} completed · {runningJobs.length} running · {failedJobs.length} failed
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <Zap className="mr-2 h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {/* Overall progress */}
      <Card>
        <CardHeader>
          <CardTitle>Overall progress</CardTitle>
          <CardDescription>
            {completedJobs.length} of {allJobs.length} jobs completed
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Progress value={totalProgress} />
          <div className="mt-2 flex justify-between text-xs text-[var(--fg-muted)]">
            <span>{totalProgress.toFixed(0)}% complete</span>
            {workflow && (
              <span>Current step: {workflow.current_step}</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Stats cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-3 py-4">
            <Clock className="h-8 w-8 text-[var(--fg-muted)]" />
            <div>
              <div className="text-2xl font-bold text-[var(--fg-default)]">{queuedJobs.length}</div>
              <div className="text-xs text-[var(--fg-muted)]">Queued</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 py-4">
            <Loader2 className="h-8 w-8 animate-spin text-[var(--fg-muted)]" />
            <div>
              <div className="text-2xl font-bold text-[var(--fg-default)]">{runningJobs.length}</div>
              <div className="text-xs text-[var(--fg-muted)]">Running</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 py-4">
            <CheckCircle2 className="h-8 w-8 text-[var(--fg-muted)]" />
            <div>
              <div className="text-2xl font-bold text-[var(--fg-default)]">{completedJobs.length}</div>
              <div className="text-xs text-[var(--fg-muted)]">Completed</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 py-4">
            <XCircle className="h-8 w-8 text-[var(--fg-muted)]" />
            <div>
              <div className="text-2xl font-bold text-[var(--fg-default)]">{failedJobs.length}</div>
              <div className="text-xs text-[var(--fg-muted)]">Failed</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Job list */}
      {allJobs.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Job queue</CardTitle>
            <CardDescription>Real-time generation job status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {allJobs.map((job) => {
                const currentStatus = realtimeJobs[job.id]?.status ?? job.status
                const config = jobStatusConfig[currentStatus] ?? jobStatusConfig.queued
                const StatusIcon = config.icon
                return (
                  <div
                    key={job.id}
                    className="flex items-center gap-4 rounded-lg border border-[var(--border-default)] p-3"
                  >
                    {/* Status icon */}
                    <StatusIcon className={`h-5 w-5 shrink-0 ${currentStatus === 'running' ? 'animate-spin' : ''} text-[var(--fg-muted)]`} />

                    {/* Job info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--fg-default)] capitalize">
                          {job.job_type.replace(/_/g, ' ')}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {job.priority}
                        </Badge>
                      </div>
                      <div className="text-xs text-[var(--fg-muted)]">
                        {job.queued_at && `Queued ${formatRelativeTime(job.queued_at)}`}
                        {job.started_at && ` · Started ${formatRelativeTime(job.started_at)}`}
                        {job.execution_time_seconds && ` · ${job.execution_time_seconds.toFixed(1)}s`}
                      </div>
                      {job.error_message && (
                        <div className="mt-1 text-xs text-[var(--fg-error)]">{job.error_message}</div>
                      )}
                    </div>

                    {/* Status badge */}
                    <Badge variant={config.variant}>
                      {config.label}
                    </Badge>

                    {/* Retry info */}
                    {job.retry_count > 0 && (
                      <span className="text-xs text-[var(--fg-muted)]">
                        Retries: {job.retry_count}/{job.max_retries}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      ) : (
        <EmptyState
          icon={<Cpu className="h-12 w-12" />}
          title="No generation jobs yet"
          description="Jobs will appear here once the workflow starts generating assets."
          action={
            <Link href={`/projects/${projectId}`}>
              <Button>Go to project</Button>
            </Link>
          }
        />
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Link href={`/projects/${projectId}/assets`}>
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to assets
          </Button>
        </Link>
        <Link href={`/projects/${projectId}`}>
          <Button>
            Back to project
          </Button>
        </Link>
      </div>
    </div>
  )
}
