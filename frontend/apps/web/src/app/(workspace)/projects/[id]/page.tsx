'use client'

import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  getSDK,
  useProject,
  useProjectWorkflow,
  useStartWorkflow,
  useCancelWorkflow,
  useAdvanceWorkflow,
  useRetryStep,
  useDeleteProject,
  useResearch,
  useScript,
  useStoryboard,
  useScenes,
  useAssets,
  useGenerationJobs,
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
  Dialog,
  Textarea,
  Input,
} from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import {
  ArrowLeft,
  ArrowRight,
  Play,
  XCircle,
  Trash2,
  Pencil,
  Clock,
  Tag,
  Globe,
  Users,
  Video,
  CheckCircle2,
  Circle,
  Loader2,
  BookOpen,
  FileText,
  Clapperboard,
  Image,
  Cpu,
  Layers,
  Film,
  Youtube,
  RotateCcw,
  Sparkles,
  Mic,
  Subtitles,
  Search,
  Download,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import { useState } from 'react'
import { WorkflowStep } from '@ai-video-studio/shared-types'

const workflowSteps: { step: WorkflowStep; label: string }[] = [
  { step: WorkflowStep.INITIALIZATION, label: 'Initialization' },
  { step: WorkflowStep.RESEARCH, label: 'Research' },
  { step: WorkflowStep.SCRIPTING, label: 'Scripting' },
  { step: WorkflowStep.STORYBOARD, label: 'Storyboard' },
  { step: WorkflowStep.SCENE_PLANNING, label: 'Scene Planning' },
  { step: WorkflowStep.ASSET_GENERATION, label: 'Asset Generation' },
  { step: WorkflowStep.VOICE_GENERATION, label: 'Voice Generation' },
  { step: WorkflowStep.SUBTITLE_GENERATION, label: 'Subtitles' },
  { step: WorkflowStep.RENDERING, label: 'Rendering' },
  { step: WorkflowStep.THUMBNAIL, label: 'Thumbnail' },
  { step: WorkflowStep.SEO, label: 'SEO' },
  { step: WorkflowStep.COMPLETED, label: 'Completed' },
]

function getStepStatus(currentStep: string, stepValue: string, workflowStatus?: string): 'completed' | 'active' | 'pending' {
  const currentIdx = workflowSteps.findIndex((s) => s.step === currentStep)
  const stepIdx = workflowSteps.findIndex((s) => s.step === stepValue)
  if (currentIdx === -1) return 'pending'
  if (stepIdx < currentIdx) return 'completed'
  if (stepIdx === currentIdx) return workflowStatus === 'completed' ? 'completed' : 'active'
  return 'pending'
}

const statusBadgeVariant: Record<string, 'default' | 'secondary' | 'success' | 'warning' | 'error' | 'info' | 'outline'> = {
  draft: 'secondary',
  researching: 'info',
  scripting: 'info',
  planning: 'info',
  generating: 'warning',
  rendering: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'outline',
}

const stepIcons: Record<string, typeof BookOpen> = {
  initialization: Sparkles,
  research: BookOpen,
  scripting: FileText,
  storyboard: Clapperboard,
  scene_planning: Layers,
  asset_generation: Image,
  voice_generation: Mic,
  subtitle_generation: Subtitles,
  rendering: Film,
  thumbnail: Image,
  seo: Search,
  completed: CheckCircle2,
}

function StepOutput({ projectId, currentStep }: { projectId: string; currentStep: string }) {
  const { data: research, isLoading: researchLoading } = useResearch(projectId, { enabled: currentStep === 'research' })
  const { data: script, isLoading: scriptLoading } = useScript(projectId, { enabled: currentStep === 'scripting' })
  const { data: storyboard, isLoading: sbLoading } = useStoryboard(projectId, { enabled: currentStep === 'storyboard' || currentStep === 'scene_planning' })
  const { data: scenesData } = useScenes(projectId, { enabled: currentStep === 'scene_planning' })
  const { data: assetsData } = useAssets(projectId, undefined, { enabled: currentStep === 'asset_generation' || currentStep === 'voice_generation' || currentStep === 'subtitle_generation' })
  const { data: jobsData } = useGenerationJobs(projectId, undefined, { enabled: currentStep === 'asset_generation' || currentStep === 'rendering' })

  if (currentStep === 'initialization') {
    return (
      <div className="space-y-2">
        <p className="text-sm text-[var(--fg-muted)]">Project has been initialized and is ready for research.</p>
        <div className="rounded-lg bg-[var(--bg-surface)] p-4">
          <p className="text-xs text-[var(--fg-muted)]">The workflow is now set up. Click &quot;Next Step&quot; to begin the research phase.</p>
        </div>
      </div>
    )
  }

  if (currentStep === 'research') {
    if (researchLoading) return <Skeleton className="h-32" />
    if (!research) return <p className="text-sm text-[var(--fg-muted)]">No research output yet. Click &quot;Retry Step&quot; to generate research.</p>
    return (
      <div className="space-y-3">
        <div>
          <h4 className="mb-1 text-sm font-semibold text-[var(--fg-default)]">Summary</h4>
          <p className="text-sm text-[var(--fg-muted)]">{research.summary}</p>
        </div>
        {research.timeline.length > 0 && (
          <div>
            <h4 className="mb-1 text-sm font-semibold text-[var(--fg-default)]">Timeline</h4>
            <ul className="list-inside list-disc text-sm text-[var(--fg-muted)]">
              {research.timeline.map((t, i) => <li key={i}>{t}</li>)}
            </ul>
          </div>
        )}
        {research.interesting_facts.length > 0 && (
          <div>
            <h4 className="mb-1 text-sm font-semibold text-[var(--fg-default)]">Interesting Facts</h4>
            <ul className="list-inside list-disc text-sm text-[var(--fg-muted)]">
              {research.interesting_facts.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </div>
        )}
        {research.keywords.length > 0 && (
          <div>
            <h4 className="mb-1 text-sm font-semibold text-[var(--fg-default)]">Keywords</h4>
            <div className="flex flex-wrap gap-1">
              {research.keywords.map((k, i) => <Badge key={i} variant="outline" className="text-xs">{k}</Badge>)}
            </div>
          </div>
        )}
      </div>
    )
  }

  if (currentStep === 'scripting') {
    if (scriptLoading) return <Skeleton className="h-32" />
    if (!script) return <p className="text-sm text-[var(--fg-muted)]">No script output yet. Click &quot;Retry Step&quot; to generate a script.</p>
    return (
      <div className="space-y-3">
        {script.hook && (
          <div>
            <h4 className="mb-1 text-sm font-semibold text-[var(--fg-default)]">Hook</h4>
            <p className="text-sm text-[var(--fg-muted)]">{script.hook}</p>
          </div>
        )}
        <div>
          <h4 className="mb-1 text-sm font-semibold text-[var(--fg-default)]">Body</h4>
          <p className="whitespace-pre-wrap text-sm text-[var(--fg-muted)]">{script.body}</p>
        </div>
        {script.cta && (
          <div>
            <h4 className="mb-1 text-sm font-semibold text-[var(--fg-default)]">Call to Action</h4>
            <p className="text-sm text-[var(--fg-muted)]">{script.cta}</p>
          </div>
        )}
        <div className="flex gap-4 text-xs text-[var(--fg-muted)]">
          <span>Words: {script.word_count}</span>
          <span>Est. duration: {Math.round(script.estimated_duration_seconds)}s</span>
          <span>Language: {script.language}</span>
        </div>
      </div>
    )
  }

  if (currentStep === 'storyboard') {
    if (sbLoading) return <Skeleton className="h-32" />
    if (!storyboard) return <p className="text-sm text-[var(--fg-muted)]">No storyboard output yet. Click &quot;Retry Step&quot; to generate a storyboard.</p>
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-[var(--bg-surface)] p-3">
            <div className="text-xs text-[var(--fg-muted)]">Scenes</div>
            <div className="text-lg font-bold text-[var(--fg-default)]">{storyboard.scene_count}</div>
          </div>
          <div className="rounded-lg bg-[var(--bg-surface)] p-3">
            <div className="text-xs text-[var(--fg-muted)]">Est. Duration</div>
            <div className="text-lg font-bold text-[var(--fg-default)]">{Math.round(storyboard.estimated_duration_seconds)}s</div>
          </div>
          <div className="rounded-lg bg-[var(--bg-surface)] p-3">
            <div className="text-xs text-[var(--fg-muted)]">Style</div>
            <div className="text-lg font-bold text-[var(--fg-default)]">{storyboard.style}</div>
          </div>
        </div>
        <div>
          <h4 className="mb-1 text-sm font-semibold text-[var(--fg-default)]">Narrative Structure</h4>
          <p className="text-sm text-[var(--fg-muted)]">{storyboard.narrative_structure}</p>
        </div>
        {storyboard.pacing_notes && (
          <div>
            <h4 className="mb-1 text-sm font-semibold text-[var(--fg-default)]">Pacing Notes</h4>
            <p className="text-sm text-[var(--fg-muted)]">{storyboard.pacing_notes}</p>
          </div>
        )}
      </div>
    )
  }

  if (currentStep === 'scene_planning') {
    const scenes = scenesData?.items ?? []
    if (scenes.length === 0) return <p className="text-sm text-[var(--fg-muted)]">No scenes generated yet.</p>
    return (
      <div className="space-y-2">
        {scenes.map((scene, i) => (
          <div key={scene.id ?? i} className="rounded-lg border border-[var(--border-default)] p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-[var(--fg-default)]">Scene {scene.scene_number}: {scene.title}</span>
              <Badge variant="outline" className="text-xs">{scene.duration_seconds}s</Badge>
            </div>
            <p className="mt-1 text-xs text-[var(--fg-muted)]">{scene.narration}</p>
            <div className="mt-2 flex gap-2 text-xs text-[var(--fg-muted)]">
              <span>Visual: {scene.visual_type}</span>
              <span>Emotion: {scene.emotion}</span>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (currentStep === 'asset_generation' || currentStep === 'voice_generation' || currentStep === 'subtitle_generation') {
    const assets = assetsData?.items ?? []
    if (assets.length === 0) return <p className="text-sm text-[var(--fg-muted)]">No assets generated yet. Click &quot;Retry Step&quot; to generate assets.</p>
    return (
      <div className="grid gap-2 md:grid-cols-2">
        {assets.map((asset, i) => (
          <div key={asset.id ?? i} className="rounded-lg border border-[var(--border-default)] p-3">
            <div className="flex items-center justify-between">
              <Badge variant="outline" className="text-xs">{asset.asset_type}</Badge>
              <Badge variant={asset.generation_status === 'completed' ? 'success' : 'warning'} className="text-xs">{asset.generation_status}</Badge>
            </div>
            <p className="mt-1 truncate text-xs text-[var(--fg-muted)]">{asset.storage_ref}</p>
          </div>
        ))}
      </div>
    )
  }

  if (currentStep === 'rendering') {
    const jobs = jobsData ?? []
    if (jobs.length === 0) return <p className="text-sm text-[var(--fg-muted)]">No render jobs yet. Click &quot;Retry Step&quot; to start rendering.</p>
    return (
      <div className="space-y-2">
        {jobs.map((job, i) => (
          <div key={job.id ?? i} className="rounded-lg border border-[var(--border-default)] p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-[var(--fg-default)]">{job.job_type}</span>
              <Badge variant={job.status === 'completed' ? 'success' : job.status === 'failed' ? 'error' : 'warning'} className="text-xs">{job.status}</Badge>
            </div>
            {job.error_message && <p className="mt-1 text-xs text-[var(--status-error)]">{job.error_message}</p>}
          </div>
        ))}
      </div>
    )
  }

  if (currentStep === 'completed') {
    return (
      <div className="flex flex-col items-center justify-center py-8">
        <CheckCircle2 className="mb-3 h-12 w-12 text-[var(--status-success)]" />
        <p className="text-lg font-semibold text-[var(--fg-default)]">Workflow Complete!</p>
        <p className="text-sm text-[var(--fg-muted)]">Your video project has been fully generated.</p>
      </div>
    )
  }

  return (
    <p className="text-sm text-[var(--fg-muted)]">Output for this step will appear here once available.</p>
  )
}

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const { addToast } = useToast()
  const projectId = params.id

  const { data: project, isLoading } = useProject(projectId, {
    staleTime: 0,
    refetchInterval: (query) => {
      const p = query.state.data
      const activeStatuses = ['researching', 'scripting', 'planning', 'generating', 'rendering']
      return p && activeStatuses.includes(p.status) ? 1500 : false
    },
    refetchIntervalInBackground: true,
  })
  const { data: workflow } = useProjectWorkflow(projectId, {
    staleTime: 0,
    refetchInterval: (query) => {
      const w = query.state.data
      return w && (w.status === 'pending' || w.status === 'running' || w.status === 'paused') ? 1500 : false
    },
    refetchIntervalInBackground: true,
  })
  const startWorkflow = useStartWorkflow({
    onSuccess: () => addToast({ title: 'Workflow started', variant: 'success' }),
    onError: (err) => addToast({ title: 'Failed to start workflow', description: err.message, variant: 'error' }),
  })
  const cancelWorkflow = useCancelWorkflow({
    onSuccess: () => addToast({ title: 'Workflow cancelled', variant: 'success' }),
    onError: (err) => addToast({ title: 'Failed to cancel workflow', description: err.message, variant: 'error' }),
  })
  const advanceWorkflow = useAdvanceWorkflow({
    onSuccess: () => addToast({ title: 'Moved to next step', variant: 'success' }),
    onError: (err) => addToast({ title: 'Failed to advance', description: err.message, variant: 'error' }),
  })
  const retryStep = useRetryStep({
    onSuccess: () => addToast({ title: 'Step retry started', variant: 'info' }),
    onError: (err) => addToast({ title: 'Failed to retry', description: err.message, variant: 'error' }),
  })
  const deleteProject = useDeleteProject({
    onSuccess: () => {
      addToast({ title: 'Project deleted', variant: 'success' })
      router.push('/projects')
    },
    onError: (err) => addToast({ title: 'Failed to delete project', description: err.message, variant: 'error' }),
  })

  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [editForm, setEditForm] = useState({ title: '', description: '' })

  const handleEdit = () => {
    if (project) {
      setEditForm({ title: project.title, description: project.description })
      setEditOpen(true)
    }
  }

  const handleDownload = async () => {
    try {
      const blob = await getSDK().projects.downloadOutputs(projectId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${project?.title ?? 'project'}_outputs.zip`
      a.click()
      URL.revokeObjectURL(url)
      addToast({ title: 'Outputs downloaded', variant: 'success' })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      addToast({ title: 'Download failed', description: message, variant: 'error' })
    }
  }

  const handleDownloadVideo = async () => {
    try {
      const blob = await getSDK().projects.downloadVideo(projectId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${project?.title ?? 'project'}_final.mp4`
      a.click()
      URL.revokeObjectURL(url)
      addToast({ title: 'Video downloaded', variant: 'success' })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      addToast({ title: 'Video download failed', description: message, variant: 'error' })
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
        <Skeleton className="h-96" />
      </div>
    )
  }

  if (!project) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <p className="text-sm text-[var(--fg-muted)]">Project not found</p>
          <Link href="/projects" className="mt-4 inline-block">
            <Button variant="outline">Back to Projects</Button>
          </Link>
        </div>
      </div>
    )
  }

  const isWorkflowActive = workflow != null && (workflow.status === 'pending' || workflow.status === 'running' || workflow.status === 'paused')
  const isWorkflowCompleted = workflow?.status === 'completed' || project.status === 'completed'
  const currentStep = workflow?.current_step ?? project.current_step ?? 'initialization'
  const currentStepIdx = workflowSteps.findIndex((s) => s.step === currentStep)
  const isLastStep = currentStepIdx >= workflowSteps.length - 1
  const CurrentStepIcon = stepIcons[currentStep] ?? Circle

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Link href="/projects">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>
            <h1 className="text-2xl font-bold text-[var(--fg-default)]">{project.title}</h1>
            <Badge variant={statusBadgeVariant[project.status] ?? 'default'}>{project.status}</Badge>
          </div>
          <p className="text-sm text-[var(--fg-muted)]">{project.description || 'No description'}</p>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleEdit}>
            <Pencil className="mr-2 h-3.5 w-3.5" />
            Edit
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-[var(--status-error)]"
            onClick={() => setDeleteOpen(true)}
          >
            <Trash2 className="mr-2 h-3.5 w-3.5" />
            Delete
          </Button>
        </div>
      </div>

      {/* Meta Info */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-2 p-3">
            <Globe className="h-4 w-4 text-[var(--fg-muted)]" />
            <div>
              <div className="text-xs text-[var(--fg-muted)]">Language</div>
              <div className="text-sm font-medium text-[var(--fg-default)]">{project.language}</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-2 p-3">
            <Video className="h-4 w-4 text-[var(--fg-muted)]" />
            <div>
              <div className="text-xs text-[var(--fg-muted)]">Content Type</div>
              <div className="text-sm font-medium text-[var(--fg-default)]">{project.content_type}</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-2 p-3">
            <Users className="h-4 w-4 text-[var(--fg-muted)]" />
            <div>
              <div className="text-xs text-[var(--fg-muted)]">Audience</div>
              <div className="text-sm font-medium text-[var(--fg-default)]">{project.audience || '—'}</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-2 p-3">
            <Clock className="h-4 w-4 text-[var(--fg-muted)]" />
            <div>
              <div className="text-xs text-[var(--fg-muted)]">Created</div>
              <div className="text-sm font-medium text-[var(--fg-default)]">{formatRelativeTime(project.created_at)}</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tags */}
      {project.tags.length > 0 && (
        <div className="flex items-center gap-2">
          <Tag className="h-4 w-4 text-[var(--fg-muted)]" />
          <div className="flex flex-wrap gap-1">
            {project.tags.map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
            ))}
          </div>
        </div>
      )}

      {/* Content Navigation */}
      <div className="flex flex-wrap gap-2 border-b border-[var(--border-default)] pb-3">
        <Link href={`/projects/${projectId}/research`}>
          <Button variant="ghost" size="sm">
            <BookOpen className="mr-2 h-3.5 w-3.5" />
            Research
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/script`}>
          <Button variant="ghost" size="sm">
            <FileText className="mr-2 h-3.5 w-3.5" />
            Script
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/storyboard`}>
          <Button variant="ghost" size="sm">
            <Clapperboard className="mr-2 h-3.5 w-3.5" />
            Storyboard
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/assets`}>
          <Button variant="ghost" size="sm">
            <Image className="mr-2 h-3.5 w-3.5" />
            Assets
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/generation`}>
          <Button variant="ghost" size="sm">
            <Cpu className="mr-2 h-3.5 w-3.5" />
            Generation
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/timeline`}>
          <Button variant="ghost" size="sm">
            <Layers className="mr-2 h-3.5 w-3.5" />
            Timeline
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/rendering`}>
          <Button variant="ghost" size="sm">
            <Film className="mr-2 h-3.5 w-3.5" />
            Rendering
          </Button>
        </Link>
      </div>

      {/* Workflow Actions */}
      <div className="flex gap-2">
        {!isWorkflowActive && !isWorkflowCompleted && (
          <Button onClick={() => startWorkflow.mutate(projectId)} disabled={startWorkflow.isPending}>
            <Play className="mr-2 h-4 w-4" />
            {startWorkflow.isPending ? 'Starting...' : 'Start Workflow'}
          </Button>
        )}
        {isWorkflowActive && (
          <Button
            variant="destructive"
            onClick={() => cancelWorkflow.mutate(projectId)}
            disabled={cancelWorkflow.isPending}
          >
            <XCircle className="mr-2 h-4 w-4" />
            {cancelWorkflow.isPending ? 'Cancelling...' : 'Cancel Workflow'}
          </Button>
        )}
      </div>

      {/* Current Step Output Panel */}
      {workflow && (
        <Card className="border-[var(--brand-default)]">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--brand-surface)]">
                  <CurrentStepIcon className="h-5 w-5 text-[var(--brand-default)]" />
                </div>
                <div>
                  <CardTitle className="text-lg">
                    {workflowSteps.find((s) => s.step === currentStep)?.label ?? currentStep}
                  </CardTitle>
                  <CardDescription>
                    Step {currentStepIdx + 1} of {workflowSteps.length} • Status: {workflow.status}
                    {workflow.retry_count > 0 && ` • Retries: ${workflow.retry_count}`}
                  </CardDescription>
                </div>
              </div>
              <Badge variant={workflow.status === 'completed' ? 'success' : workflow.status === 'failed' ? 'error' : 'info'}>
                {workflow.status}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="min-h-[120px] rounded-lg bg-[var(--bg-surface)] p-4">
              <StepOutput projectId={projectId} currentStep={currentStep} />
              {currentStep === 'completed' && (
                <div className="mt-4 flex justify-center gap-2">
                  <Button onClick={handleDownloadVideo}>
                    <Download className="mr-2 h-4 w-4" />
                    Download Video
                  </Button>
                  <Button onClick={handleDownload} variant="outline">
                    Download outputs (zip)
                  </Button>
                </div>
              )}
            </div>
            {/* Step Action Buttons */}
            {isWorkflowActive && !isLastStep && (
              <div className="mt-4 flex gap-2">
                <Button
                  onClick={() => advanceWorkflow.mutate(projectId)}
                  disabled={advanceWorkflow.isPending}
                >
                  <ArrowRight className="mr-2 h-4 w-4" />
                  {advanceWorkflow.isPending ? 'Advancing...' : 'Next Step'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => retryStep.mutate(projectId)}
                  disabled={retryStep.isPending}
                >
                  <RotateCcw className="mr-2 h-4 w-4" />
                  {retryStep.isPending ? 'Retrying...' : 'Retry Step'}
                </Button>
              </div>
            )}
            {isWorkflowActive && isLastStep && (
              <div className="mt-4 flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => retryStep.mutate(projectId)}
                  disabled={retryStep.isPending}
                >
                  <RotateCcw className="mr-2 h-4 w-4" />
                  {retryStep.isPending ? 'Retrying...' : 'Retry Step'}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Workflow Step List */}
      <Card>
        <CardHeader>
          <CardTitle>Workflow Progress</CardTitle>
          <CardDescription>
            {workflow ? `Current: ${workflowSteps.find((s) => s.step === workflow.current_step)?.label ?? workflow.current_step}` : 'No workflow started yet'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            {workflowSteps.map((ws, idx) => {
              const status = getStepStatus(currentStep, ws.step, workflow?.status)
              const StepIcon = stepIcons[ws.step] ?? Circle
              return (
                <div key={ws.step} className="flex items-center gap-3">
                  <div className="flex flex-col items-center">
                    {status === 'completed' && (
                      <CheckCircle2 className="h-5 w-5 text-[var(--status-success)]" />
                    )}
                    {status === 'active' && (
                      <div className="flex h-5 w-5 animate-bounce items-center justify-center rounded-full bg-[var(--brand-default)] shadow">
                        <StepIcon className="h-3 w-3 text-white" />
                      </div>
                    )}
                    {status === 'pending' && (
                      <Circle className="h-5 w-5 text-[var(--fg-muted)]" />
                    )}
                    {idx < workflowSteps.length - 1 && (
                      <div
                        className={`h-6 w-0.5 ${
                          status === 'completed' ? 'bg-[var(--status-success)]' : 'bg-[var(--border-default)]'
                        }`}
                      />
                    )}
                  </div>
                  <span
                    className={`text-sm ${
                      status === 'completed'
                        ? 'text-[var(--fg-default)]'
                        : status === 'active'
                        ? 'font-medium text-[var(--brand-default)]'
                        : 'text-[var(--fg-muted)]'
                    }`}
                  >
                    {ws.label}
                  </span>
                  {status === 'active' && workflow?.status === 'running' && (
                    <Loader2 className="h-3 w-3 animate-spin text-[var(--brand-default)]" />
                  )}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} title="Edit Project">
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium">Title</label>
            <Input
              value={editForm.title}
              onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium">Description</label>
            <Textarea
              value={editForm.description}
              onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
              rows={4}
            />
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={() => setEditOpen(false)}>Cancel</Button>
          <Button
            onClick={() => {
              import('@ai-video-studio/platform-sdk').then(({ getSDK }) => {
                getSDK().projects.update(projectId, editForm).then(() => {
                  addToast({ title: 'Project updated', variant: 'success' })
                  setEditOpen(false)
                })
              })
            }}
          >
            Save Changes
          </Button>
        </div>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteOpen} onClose={() => setDeleteOpen(false)} title="Delete Project">
        <p className="text-sm text-[var(--fg-muted)]">
          Are you sure you want to delete &quot;{project.title}&quot;? This action cannot be undone.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={() => setDeleteOpen(false)}>Cancel</Button>
          <Button
            variant="destructive"
            onClick={() => deleteProject.mutate(projectId)}
            disabled={deleteProject.isPending}
          >
            {deleteProject.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Dialog>
    </div>
  )
}
