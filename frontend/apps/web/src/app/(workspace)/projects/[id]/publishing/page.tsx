'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import {
  usePublishingPlans,
  usePublishingJobs,
  usePublishingReports,
  useCreatePublishingPlan,
  useExecutePublishing,
  useCancelPublishingJob,
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
  Input,
  Textarea,
  Select,
  Label,
} from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import { realtimeProvider } from '@ai-video-studio/platform-kernel'
import {
  ArrowLeft,
  Youtube,
  UploadCloud,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  AlertCircle,
  CalendarClock,
  Globe,
  Tag,
  ExternalLink,
  Zap,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import type { PublishingJobDTO, PublishingReportDTO } from '@ai-video-studio/shared-types'

const publishingStatusConfig: Record<string, { variant: 'default' | 'secondary' | 'success' | 'warning' | 'error'; label: string }> = {
  queued: { variant: 'secondary', label: 'Queued' },
  authenticating: { variant: 'warning', label: 'Authenticating' },
  validating: { variant: 'warning', label: 'Validating' },
  uploading: { variant: 'warning', label: 'Uploading' },
  processing: { variant: 'warning', label: 'Processing' },
  completed: { variant: 'success', label: 'Published' },
  failed: { variant: 'error', label: 'Failed' },
  cancelled: { variant: 'secondary', label: 'Cancelled' },
  draft_saved: { variant: 'secondary', label: 'Draft Saved' },
}

export default function PublishingPage() {
  const params = useParams()
  const projectId = params.id as string
  const { addToast } = useToast()

  // Publishing form state
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [tags, setTags] = useState('')
  const [privacy, setPrivacy] = useState('private')
  const [mode, setMode] = useState('immediate')
  const [scheduledAt, setScheduledAt] = useState('')
  const [realtimeStatus, setRealtimeStatus] = useState<Record<string, string>>({})

  const { data: plans, isLoading: plansLoading } = usePublishingPlans(projectId)
  const { data: jobs, isLoading: jobsLoading } = usePublishingJobs(projectId)
  const { data: reports, isLoading: reportsLoading } = usePublishingReports(projectId)

  const createPlan = useCreatePublishingPlan()
  const executePublishing = useExecutePublishing()
  const cancelJob = useCancelPublishingJob()

  // Realtime subscription
  useEffect(() => {
    const unsubscribe = realtimeProvider.on('publishing:status', (data: Record<string, unknown>) => {
      if (data.project_id === projectId) {
        setRealtimeStatus((prev) => ({
          ...prev,
          [data.id as string]: data.status as string,
        }))
        if (data.status === 'completed') {
          addToast({ title: 'Publishing completed!', variant: 'success' })
        } else if (data.status === 'failed') {
          addToast({ title: 'Publishing failed', variant: 'error' })
        }
      }
    })
    return unsubscribe
  }, [projectId, addToast])

  const handleCreatePlan = () => {
    if (!title.trim()) {
      addToast({ title: 'Title is required', variant: 'error' })
      return
    }
    createPlan.mutate(
      {
        projectId,
        body: {
          project_id: projectId,
          platform: 'youtube',
          mode,
          metadata: {
            title,
            description,
            tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
            privacy_status: privacy,
          },
          scheduled_at: mode === 'scheduled' && scheduledAt ? scheduledAt : undefined,
        },
      },
      {
        onSuccess: () => addToast({ title: 'Publishing plan created', variant: 'success' }),
        onError: () => addToast({ title: 'Failed to create plan', variant: 'error' }),
      }
    )
  }

  const handleExecute = (planId: string) => {
    executePublishing.mutate(
      { projectId, planId },
      {
        onSuccess: () => addToast({ title: 'Publishing started', variant: 'success' }),
        onError: () => addToast({ title: 'Failed to start publishing', variant: 'error' }),
      }
    )
  }

  const handleCancel = (jobId: string) => {
    cancelJob.mutate(
      { projectId, jobId },
      {
        onSuccess: () => addToast({ title: 'Publishing job cancelled', variant: 'info' }),
      }
    )
  }

  if (plansLoading || jobsLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-96 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  const allJobs = jobs ?? []
  const allReports = reports ?? []

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
            <h1 className="text-xl font-bold text-[var(--fg-default)]">Publishing</h1>
            <p className="text-sm text-[var(--fg-muted)]">
              {allJobs.length} jobs · {allReports.length} reports
            </p>
          </div>
        </div>
      </div>

      {/* Create publishing plan */}
      <Card>
        <CardHeader>
          <CardTitle>Create publishing plan</CardTitle>
          <CardDescription>Configure metadata and publish your video to YouTube</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="pub-title">Title</Label>
              <Input
                id="pub-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter video title"
                maxLength={100}
              />
              <span className="text-xs text-[var(--fg-muted)]">{title.length}/100</span>
            </div>

            <div className="space-y-2">
              <Label htmlFor="pub-tags">Tags (comma-separated)</Label>
              <Input
                id="pub-tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="technology, AI, tutorial"
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="pub-desc">Description</Label>
              <Textarea
                id="pub-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Enter video description"
                rows={4}
                maxLength={5000}
              />
              <span className="text-xs text-[var(--fg-muted)]">{description.length}/5000</span>
            </div>

            <div className="space-y-2">
              <Label htmlFor="pub-privacy">Privacy status</Label>
              <Select id="pub-privacy" value={privacy} onChange={(e) => setPrivacy(e.target.value)}>
                <option value="private">Private</option>
                <option value="unlisted">Unlisted</option>
                <option value="public">Public</option>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="pub-mode">Publishing mode</Label>
              <Select id="pub-mode" value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="immediate">Immediate</option>
                <option value="scheduled">Scheduled</option>
              </Select>
            </div>

            {mode === 'scheduled' && (
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="pub-schedule">Schedule date & time</Label>
                <Input
                  id="pub-schedule"
                  type="datetime-local"
                  value={scheduledAt}
                  onChange={(e) => setScheduledAt(e.target.value)}
                />
              </div>
            )}
          </div>

          <div className="mt-4 flex items-center gap-2">
            <Button onClick={handleCreatePlan} disabled={createPlan.isPending || !title.trim()}>
              {createPlan.isPending ? 'Creating...' : 'Create publishing plan'}
            </Button>
            <Badge variant="outline">
              <Youtube className="mr-1 h-3 w-3" />
              YouTube
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Publishing plans */}
      {plans && plans.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Publishing plans</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {plans.map((plan) => (
                <div
                  key={plan.id}
                  className="rounded-lg border border-[var(--border-default)] p-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--fg-default)]">
                        Plan {plan.id.slice(0, 8)}...
                      </span>
                      <Badge variant="outline" className="capitalize">{plan.mode}</Badge>
                      <Badge variant="secondary">{plan.platform_count} platform(s)</Badge>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleExecute(plan.id)}
                      disabled={executePublishing.isPending}
                    >
                      <UploadCloud className="mr-1 h-3 w-3" />
                      Execute
                    </Button>
                  </div>

                  {plan.validation_errors.length > 0 && (
                    <div className="mt-2 flex items-center gap-2 text-xs text-[var(--fg-error)]">
                      <AlertCircle className="h-3 w-3" />
                      {plan.validation_errors.join(', ')}
                    </div>
                  )}

                  {plan.tasks.map((task) => (
                    <div key={task.id} className="mt-3 flex items-center gap-3 text-xs">
                      <Youtube className="h-4 w-4 text-[var(--fg-muted)]" />
                      <span className="text-[var(--fg-default)]">{task.metadata.title || 'Untitled'}</span>
                      <Badge variant="outline" className="capitalize">{task.metadata.privacy_status}</Badge>
                      {task.scheduled_at && (
                        <span className="text-[var(--fg-muted)]">
                          <CalendarClock className="mr-1 inline h-3 w-3" />
                          {formatRelativeTime(task.scheduled_at)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Publishing jobs */}
      {allJobs.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Publishing jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {allJobs.map((job: PublishingJobDTO) => {
                const currentStatus = realtimeStatus[job.id] ?? job.status
                const config = publishingStatusConfig[currentStatus] ?? publishingStatusConfig.queued
                const isActive = !['completed', 'failed', 'cancelled', 'draft_saved', 'queued'].includes(currentStatus)
                return (
                  <div
                    key={job.id}
                    className="flex items-center gap-4 rounded-lg border border-[var(--border-default)] p-3"
                  >
                    {isActive ? (
                      <Loader2 className="h-5 w-5 shrink-0 animate-spin text-[var(--fg-muted)]" />
                    ) : currentStatus === 'completed' ? (
                      <CheckCircle2 className="h-5 w-5 shrink-0 text-[var(--status-success)]" />
                    ) : currentStatus === 'failed' ? (
                      <XCircle className="h-5 w-5 shrink-0 text-[var(--status-error)]" />
                    ) : (
                      <Clock className="h-5 w-5 shrink-0 text-[var(--fg-muted)]" />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--fg-default)]">
                          {job.id.slice(0, 8)}...
                        </span>
                        <Badge variant="outline" className="capitalize">{job.platform}</Badge>
                        <Badge variant="outline" className="capitalize">{job.priority}</Badge>
                      </div>
                      <div className="text-xs text-[var(--fg-muted)]">
                        {job.started_at && `Started ${formatRelativeTime(job.started_at)}`}
                        {job.execution_time_seconds > 0 && ` · ${job.execution_time_seconds.toFixed(0)}s`}
                        {job.error && <span className="text-[var(--fg-error)]"> · {job.error}</span>}
                      </div>
                    </div>
                    <Badge variant={config.variant}>{config.label}</Badge>
                    {isActive && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleCancel(job.id)}
                        disabled={cancelJob.isPending}
                      >
                        Cancel
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
          icon={<UploadCloud className="h-12 w-12" />}
          title="No publishing jobs yet"
          description="Create a publishing plan above to start publishing your video."
        />
      )}

      {/* Publishing reports */}
      {allReports.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Publishing reports</CardTitle>
            <CardDescription>Results from completed publishing operations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {allReports.map((report: PublishingReportDTO) => (
                <div
                  key={report.id}
                  className="rounded-lg border border-[var(--border-default)] p-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Youtube className="h-4 w-4 text-[var(--fg-muted)]" />
                      <span className="text-sm font-medium text-[var(--fg-default)]">
                        {report.platform}
                      </span>
                      <Badge variant={report.is_successful ? 'success' : 'error'}>
                        {report.status}
                      </Badge>
                    </div>
                    {report.video_url && (
                      <a href={report.video_url} target="_blank" rel="noopener noreferrer">
                        <Button variant="outline" size="sm">
                          <ExternalLink className="mr-1 h-3 w-3" />
                          View on YouTube
                        </Button>
                      </a>
                    )}
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-3 text-xs md:grid-cols-4">
                    <div>
                      <span className="text-[var(--fg-muted)]">Upload time</span>
                      <div className="font-medium text-[var(--fg-default)]">
                        {report.upload_duration_seconds.toFixed(1)}s
                      </div>
                    </div>
                    <div>
                      <span className="text-[var(--fg-muted)]">Total time</span>
                      <div className="font-medium text-[var(--fg-default)]">
                        {report.total_duration_seconds.toFixed(1)}s
                      </div>
                    </div>
                    <div>
                      <span className="text-[var(--fg-muted)]">Thumbnail</span>
                      <div className="font-medium text-[var(--fg-default)]">
                        {report.thumbnail_uploaded ? 'Uploaded' : 'Not uploaded'}
                      </div>
                    </div>
                    <div>
                      <span className="text-[var(--fg-muted)]">Metadata</span>
                      <div className="font-medium text-[var(--fg-default)]">
                        {report.metadata_updated ? 'Updated' : 'Not updated'}
                      </div>
                    </div>
                  </div>

                  {report.warnings.length > 0 && (
                    <div className="mt-2 text-xs text-[var(--fg-warning)]">
                      <AlertCircle className="mr-1 inline h-3 w-3" />
                      {report.warnings.join(', ')}
                    </div>
                  )}
                  {report.errors.length > 0 && (
                    <div className="mt-1 text-xs text-[var(--fg-error)]">
                      <XCircle className="mr-1 inline h-3 w-3" />
                      {report.errors.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Link href={`/projects/${projectId}/rendering`}>
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to rendering
          </Button>
        </Link>
        <Link href={`/projects/${projectId}`}>
          <Button variant="outline">
            Back to project
          </Button>
        </Link>
      </div>
    </div>
  )
}
