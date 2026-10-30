'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import {
  useRenders,
  useRenderProgress,
  useSubmitRender,
  useCancelRender,
  useComposition,
  useProjectPackage,
} from '@ai-video-studio/platform-sdk'
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
  Select,
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
  Download,
  Film,
  Gauge,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import type { RenderJobDTO } from '@ai-video-studio/shared-types'

const renderStatusConfig: Record<string, { variant: 'default' | 'secondary' | 'success' | 'warning' | 'error'; icon: typeof Clock; label: string }> = {
  queued: { variant: 'secondary', icon: Clock, label: 'Queued' },
  loading: { variant: 'warning', icon: Loader2, label: 'Loading' },
  validating: { variant: 'warning', icon: Loader2, label: 'Validating' },
  preparing: { variant: 'warning', icon: Loader2, label: 'Preparing' },
  compiling: { variant: 'warning', icon: Loader2, label: 'Compiling' },
  composing: { variant: 'warning', icon: Loader2, label: 'Composing' },
  rendering: { variant: 'warning', icon: Loader2, label: 'Rendering' },
  encoding: { variant: 'warning', icon: Loader2, label: 'Encoding' },
  validating_output: { variant: 'warning', icon: Loader2, label: 'Validating Output' },
  completed: { variant: 'success', icon: CheckCircle2, label: 'Completed' },
  failed: { variant: 'error', icon: XCircle, label: 'Failed' },
  cancelled: { variant: 'secondary', icon: XCircle, label: 'Cancelled' },
  paused: { variant: 'secondary', icon: Clock, label: 'Paused' },
}

export default function RenderingPage() {
  const params = useParams()
  const projectId = params.id as string
  const { addToast } = useToast()
  const [priority, setPriority] = useState('normal')
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [realtimeStatus, setRealtimeStatus] = useState<Record<string, string>>({})

  const { data: composition } = useComposition(projectId)
  const { data: renders, isLoading, error, refetch } = useRenders(projectId)
  const { data: projectPackage } = useProjectPackage(projectId)
  const submitRender = useSubmitRender()
  const cancelRender = useCancelRender()

  const { data: activeProgress } = useRenderProgress(
    projectId,
    activeJobId ?? '',
    { enabled: !!activeJobId }
  )

  // Realtime subscription
  useEffect(() => {
    const unsubscribe = realtimeProvider.on('render:status', (data: Record<string, unknown>) => {
      if (data.project_id === projectId) {
        setRealtimeStatus((prev) => ({
          ...prev,
          [data.id as string]: data.status as string,
        }))
        if (data.status === 'completed') {
          addToast({ title: 'Render completed', variant: 'success' })
          refetch()
        } else if (data.status === 'failed') {
          addToast({ title: 'Render failed', variant: 'error' })
          refetch()
        }
      }
    })
    return unsubscribe
  }, [projectId, addToast, refetch])

  const handleSubmitRender = () => {
    if (!composition) return
    submitRender.mutate(
      {
        projectId,
        body: {
          composition_id: composition.id,
          priority,
        },
      },
      {
        onSuccess: (job) => {
          addToast({ title: 'Render job submitted', variant: 'success' })
          setActiveJobId(job.id)
        },
        onError: () => addToast({ title: 'Failed to submit render', variant: 'error' }),
      }
    )
  }

  const handleCancel = (jobId: string) => {
    cancelRender.mutate(
      { projectId, jobId },
      {
        onSuccess: () => {
          addToast({ title: 'Render job cancelled', variant: 'info' })
          if (activeJobId === jobId) setActiveJobId(null)
        },
      }
    )
  }

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
          title="Failed to load render jobs"
          description="There was an error loading the render queue."
        />
      </div>
    )
  }

  const allJobs = renders ?? []
  const completedJobs = allJobs.filter((j) => (realtimeStatus[j.id] ?? j.status) === 'completed')
  const runningJobs = allJobs.filter((j) => {
    const s = realtimeStatus[j.id] ?? j.status
    return s !== 'queued' && s !== 'completed' && s !== 'failed' && s !== 'cancelled'
  })
  const queuedJobs = allJobs.filter((j) => (realtimeStatus[j.id] ?? j.status) === 'queued')
  const failedJobs = allJobs.filter((j) => (realtimeStatus[j.id] ?? j.status) === 'failed')

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
            <h1 className="text-xl font-bold text-[var(--fg-default)]">Render Queue</h1>
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

      {/* Submit render */}
      <Card>
        <CardHeader>
          <CardTitle>Submit new render</CardTitle>
          <CardDescription>
            {composition
              ? `Composition: ${composition.id.slice(0, 8)}... · ${composition.export_profile.resolution} · ${composition.total_duration.toFixed(1)}s`
              : 'No composition available — build one from the Timeline Editor first'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <Select value={priority} onChange={(e) => setPriority(e.target.value)} className="w-40">
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="normal">Normal</option>
              <option value="low">Low</option>
              <option value="background">Background</option>
            </Select>
            <Button
              onClick={handleSubmitRender}
              disabled={!composition || submitRender.isPending}
            >
              {submitRender.isPending ? 'Submitting...' : 'Submit render'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Active render progress */}
      {activeProgress && (
        <Card>
          <CardHeader>
            <CardTitle>Active render progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-[var(--fg-default)]">Stage: {activeProgress.current_stage}</span>
                <span className="text-[var(--fg-muted)]">{activeProgress.progress_percentage.toFixed(0)}%</span>
              </div>
              <Progress value={activeProgress.progress_percentage} />
              <div className="flex justify-between text-xs text-[var(--fg-muted)]">
                <span>{activeProgress.frames_processed} / {activeProgress.total_frames} frames</span>
                <span>ETA: {activeProgress.estimated_time_remaining.toFixed(0)}s</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {activeProgress.stages_completed.map((stage) => (
                  <Badge key={stage} variant="success" className="text-xs">{stage}</Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
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
            <CardTitle>Render jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {allJobs.map((job: RenderJobDTO) => {
                const currentStatus = realtimeStatus[job.id] ?? job.status
                const config = renderStatusConfig[currentStatus] ?? renderStatusConfig.queued
                const StatusIcon = config.icon
                const isActive = currentStatus !== 'queued' && currentStatus !== 'completed' && currentStatus !== 'failed' && currentStatus !== 'cancelled'
                return (
                  <div
                    key={job.id}
                    className="flex items-center gap-4 rounded-lg border border-[var(--border-default)] p-3"
                  >
                    <StatusIcon className={`h-5 w-5 shrink-0 ${isActive ? 'animate-spin' : ''} text-[var(--fg-muted)]`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--fg-default)]">
                          {job.id.slice(0, 8)}...
                        </span>
                        <Badge variant="outline" className="text-xs capitalize">{job.priority}</Badge>
                      </div>
                      <div className="text-xs text-[var(--fg-muted)]">
                        {job.started_at && `Started ${formatRelativeTime(job.started_at)}`}
                        {job.execution_time_seconds > 0 && ` · ${job.execution_time_seconds.toFixed(1)}s`}
                        {job.error && <span className="text-[var(--fg-error)]"> · {job.error}</span>}
                      </div>
                    </div>
                    <Badge variant={config.variant}>{config.label}</Badge>
                    {job.retry_count > 0 && (
                      <span className="text-xs text-[var(--fg-muted)]">Retries: {job.retry_count}</span>
                    )}
                    {isActive && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleCancel(job.id)}
                        disabled={cancelRender.isPending}
                      >
                        Cancel
                      </Button>
                    )}
                    {currentStatus === 'completed' && (
                      <Button variant="outline" size="sm" onClick={() => addToast({ title: 'Download started', variant: 'info' })}>
                        <Download className="mr-1 h-3 w-3" />
                        Download
                      </Button>
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
          title="No render jobs yet"
          description="Submit a render job to start producing your final video."
        />
      )}

      {/* Project package */}
      {projectPackage && (
        <Card>
          <CardHeader>
            <CardTitle>Project package</CardTitle>
            <CardDescription>Final output from rendering</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <div>
                <div className="text-xs text-[var(--fg-muted)]">Status</div>
                <div className="text-sm font-medium text-[var(--fg-default)]">
                  {projectPackage.is_complete ? 'Complete' : 'Incomplete'}
                </div>
              </div>
              <div>
                <div className="text-xs text-[var(--fg-muted)]">Video</div>
                <div className="text-sm font-medium text-[var(--fg-default)] truncate">
                  {projectPackage.final_video_path || 'Not rendered'}
                </div>
              </div>
              <div>
                <div className="text-xs text-[var(--fg-muted)]">Thumbnail</div>
                <div className="text-sm font-medium text-[var(--fg-default)] truncate">
                  {projectPackage.thumbnail_path || 'None'}
                </div>
              </div>
              <div>
                <div className="text-xs text-[var(--fg-muted)]">Subtitles</div>
                <div className="text-sm font-medium text-[var(--fg-default)]">
                  {projectPackage.subtitle_files.length} files
                </div>
              </div>
            </div>
            {projectPackage.quality_report && (
              <div className="mt-4 flex items-center gap-2">
                <Gauge className="h-4 w-4 text-[var(--fg-muted)]" />
                {projectPackage.quality_report.overall_pass ? (
                  <Badge variant="success">Quality check passed</Badge>
                ) : (
                  <Badge variant="error">Quality issues detected</Badge>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Link href={`/projects/${projectId}/timeline`}>
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to timeline
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/publishing`}>
          <Button>
            Continue to publishing
          </Button>
        </Link>
      </div>
    </div>
  )
}
