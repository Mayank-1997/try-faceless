'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useState } from 'react'
import { useStoryboard, useStoryboardVersions, useScenes, useUpdateScene } from '@ai-video-studio/platform-sdk'
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
  Textarea,
  Input,
  Dialog,
} from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import {
  ArrowLeft,
  Clapperboard,
  RefreshCw,
  Clock,
  Camera,
  Film,
  Layers,
  Pencil,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import type { SceneResponse } from '@ai-video-studio/shared-types'

export default function StoryboardPage() {
  const params = useParams()
  const projectId = params.id as string
  const { addToast } = useToast()
  const [showVersions, setShowVersions] = useState(false)
  const [editScene, setEditScene] = useState<SceneResponse | null>(null)
  const [editNarration, setEditNarration] = useState('')

  const { data: storyboard, isLoading, error, refetch } = useStoryboard(projectId)
  const { data: versions } = useStoryboardVersions(projectId)
  const { data: scenesData } = useScenes(projectId)
  const updateScene = useUpdateScene()

  const handleRegenerate = () => {
    addToast({ title: 'Storyboard regeneration started', variant: 'info' })
    refetch()
  }

  const handleSaveScene = () => {
    if (!editScene) return
    updateScene.mutate(
      { projectId, sceneId: editScene.id, updates: { narration: editNarration } },
      {
        onSuccess: () => {
          addToast({ title: 'Scene updated', variant: 'success' })
          setEditScene(null)
        },
        onError: () => {
          addToast({ title: 'Failed to update scene', variant: 'error' })
        },
      }
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    )
  }

  if (error || !storyboard) {
    return (
      <div className="p-6">
        <Link href={`/projects/${projectId}`} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--fg-muted)] hover:text-[var(--fg-default)]">
          <ArrowLeft className="h-4 w-4" />
          Back to project
        </Link>
        <EmptyState
          icon={<Clapperboard className="h-12 w-12" />}
          title="No storyboard available"
          description="The workflow needs to reach the storyboard step."
          action={
            <Link href={`/projects/${projectId}`}>
              <Button>Go to project</Button>
            </Link>
          }
        />
      </div>
    )
  }

  const scenes = scenesData?.items ?? []
  let plannedScenes: Array<{ scene_number: number; visual_prompt_summary: string; metadata?: { clip_beats?: string[] } }> = []
  try {
    plannedScenes = storyboard.package_json ? JSON.parse(storyboard.package_json).scene_packages ?? [] : []
  } catch {
    plannedScenes = []
  }

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
            <h1 className="text-xl font-bold text-[var(--fg-default)]">Storyboard</h1>
            <p className="text-sm text-[var(--fg-muted)]">
              Version {storyboard.version} · {storyboard.scene_count} scenes · Updated {formatRelativeTime(storyboard.updated_at)}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowVersions(!showVersions)}
          >
            {showVersions ? 'Hide versions' : `Versions (${versions?.length ?? 0})`}
          </Button>
          <Button variant="outline" size="sm" onClick={handleRegenerate}>
            <RefreshCw className="mr-2 h-3.5 w-3.5" />
            Regenerate
          </Button>
        </div>
      </div>

      {/* Version history */}
      {showVersions && versions && versions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Storyboard versions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {versions.map((v) => (
                <div
                  key={v.id}
                  className="flex items-center justify-between rounded-lg border border-[var(--border-default)] p-3"
                >
                  <div>
                    <span className="font-medium text-[var(--fg-default)]">Version {v.version}</span>
                    <span className="ml-2 text-sm text-[var(--fg-muted)]">
                      {v.scene_count} scenes · {formatRelativeTime(v.updated_at)}
                    </span>
                  </div>
                  <Badge variant={v.status === 'approved' ? 'success' : 'secondary'}>
                    {v.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {plannedScenes.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Generation scene packages</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {plannedScenes.map((scene) => (
              <div key={scene.scene_number} className="space-y-1 text-sm text-[var(--fg-default)]">
                <strong>Scene {scene.scene_number}</strong>
                <p>{scene.visual_prompt_summary}</p>
                {scene.metadata?.clip_beats?.map((beat, index) => <p key={index}>Clip {index + 1}: {beat}</p>)}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Storyboard metadata */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="flex items-center gap-3 py-4">
            <Layers className="h-8 w-8 text-[var(--fg-muted)]" />
            <div>
              <div className="text-2xl font-bold text-[var(--fg-default)]">{storyboard.scene_count}</div>
              <div className="text-xs text-[var(--fg-muted)]">Scenes</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 py-4">
            <Clock className="h-8 w-8 text-[var(--fg-muted)]" />
            <div>
              <div className="text-2xl font-bold text-[var(--fg-default)]">
                {Math.floor(storyboard.estimated_duration_seconds / 60)}m {storyboard.estimated_duration_seconds % 60}s
              </div>
              <div className="text-xs text-[var(--fg-muted)]">Est. duration</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 py-4">
            <Film className="h-8 w-8 text-[var(--fg-muted)]" />
            <div>
              <div className="text-lg font-bold text-[var(--fg-default)]">{storyboard.style}</div>
              <div className="text-xs text-[var(--fg-muted)]">Style</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="text-xs text-[var(--fg-muted)]">Narrative structure</div>
            <div className="mt-1 text-sm font-medium text-[var(--fg-default)]">{storyboard.narrative_structure}</div>
            {storyboard.pacing_notes && (
              <div className="mt-2 text-xs text-[var(--fg-muted)]">{storyboard.pacing_notes}</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Scene cards */}
      {scenes.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {scenes.map((scene) => (
            <Card key={scene.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">
                    Scene {scene.scene_number}
                  </CardTitle>
                  <Badge variant="secondary">{scene.visual_type}</Badge>
                </div>
                <CardDescription>{scene.title}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {/* Narration */}
                  <div>
                    <div className="mb-1 text-xs font-medium text-[var(--fg-muted)]">Narration</div>
                    <p className="line-clamp-3 text-sm text-[var(--fg-default)]">{scene.narration}</p>
                  </div>

                  {/* Camera info */}
                  {(scene.camera_angle || scene.camera_motion) && (
                    <div className="flex items-center gap-2 text-xs text-[var(--fg-muted)]">
                      <Camera className="h-3.5 w-3.5" />
                      {scene.camera_angle && <span>{scene.camera_angle}</span>}
                      {scene.camera_angle && scene.camera_motion && <span>·</span>}
                      {scene.camera_motion && <span>{scene.camera_motion}</span>}
                    </div>
                  )}

                  {/* Duration & emotion */}
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[var(--fg-muted)]">
                      <Clock className="mr-1 inline h-3 w-3" />
                      {scene.duration_seconds.toFixed(1)}s
                    </span>
                    <Badge variant="outline">{scene.emotion}</Badge>
                  </div>

                  {/* Status badges */}
                  <div className="flex gap-1.5">
                    <Badge variant={scene.generation_status === 'completed' ? 'success' : scene.generation_status === 'pending' ? 'secondary' : 'warning'}>
                      {scene.generation_status}
                    </Badge>
                    <Badge variant={scene.review_status === 'approved' ? 'success' : 'secondary'}>
                      {scene.review_status}
                    </Badge>
                  </div>

                  {/* Edit button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full"
                    onClick={() => {
                      setEditScene(scene)
                      setEditNarration(scene.narration)
                    }}
                  >
                    <Pencil className="mr-2 h-3 w-3" />
                    Edit narration
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Layers className="h-12 w-12" />}
          title="No scenes yet"
          description="Scenes will appear here once the storyboard is generated."
        />
      )}

      {/* Edit scene dialog */}
      <Dialog
        open={!!editScene}
        onClose={() => setEditScene(null)}
        title={`Edit Scene ${editScene?.scene_number}`}
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium">Narration</label>
            <Textarea
              value={editNarration}
              onChange={(e) => setEditNarration(e.target.value)}
              rows={6}
            />
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={() => setEditScene(null)}>Cancel</Button>
          <Button onClick={handleSaveScene} disabled={updateScene.isPending}>
            {updateScene.isPending ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </Dialog>

      {/* Navigation */}
      <div className="flex justify-between">
        <Link href={`/projects/${projectId}/script`}>
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to script
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/assets`}>
          <Button>
            Continue to assets
          </Button>
        </Link>
      </div>
    </div>
  )
}
