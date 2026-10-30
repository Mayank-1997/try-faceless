'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useState } from 'react'
import {
  useComposition,
  useBuildComposition,
  useUpdateTimeline,
  useGeneratePreview,
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
  Select,
} from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import {
  ArrowLeft,
  Layers,
  Film,
  Video,
  Image as ImageIcon,
  Mic,
  Music,
  Subtitles,
  Scissors,
  SplitSquareHorizontal,
  Eye,
  Clock,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Gauge,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import type { TrackDTO } from '@ai-video-studio/shared-types'

const trackTypeConfig: Record<string, { icon: typeof Video; color: string; label: string }> = {
  video: { icon: Video, color: 'var(--status-info)', label: 'Video' },
  image: { icon: ImageIcon, color: 'var(--status-warning)', label: 'Images' },
  voice: { icon: Mic, color: 'var(--status-success)', label: 'Voice' },
  music: { icon: Music, color: 'var(--status-info)', label: 'Music' },
  sound_effect: { icon: Music, color: 'var(--status-warning)', label: 'SFX' },
  subtitle: { icon: Subtitles, color: 'var(--fg-muted)', label: 'Subtitles' },
  overlay: { icon: Layers, color: 'var(--status-error)', label: 'Overlays' },
  animation: { icon: Film, color: 'var(--status-success)', label: 'Animation' },
  custom: { icon: Layers, color: 'var(--fg-muted)', label: 'Custom' },
}

const exportPresets = ['1080p', '1440p', '4k', 'square', 'portrait']

export default function TimelinePage() {
  const params = useParams()
  const projectId = params.id as string
  const { addToast } = useToast()
  const [selectedTrack, setSelectedTrack] = useState<string | null>(null)
  const [exportPreset, setExportPreset] = useState('1080p')

  const { data: composition, isLoading, error } = useComposition(projectId)
  const buildComposition = useBuildComposition()
  const updateTimeline = useUpdateTimeline()
  const generatePreview = useGeneratePreview()

  const handleBuild = () => {
    buildComposition.mutate(
      { projectId, body: { project_id: projectId, export_preset: exportPreset } },
      {
        onSuccess: () => addToast({ title: 'Composition built', variant: 'success' }),
        onError: () => addToast({ title: 'Failed to build composition', variant: 'error' }),
      }
    )
  }

  const handlePreview = () => {
    if (!composition) return
    generatePreview.mutate(
      { projectId, compositionId: composition.id },
      {
        onSuccess: () => addToast({ title: 'Preview generated', variant: 'success' }),
        onError: () => addToast({ title: 'Failed to generate preview', variant: 'error' }),
      }
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (error || !composition) {
    return (
      <div className="p-6">
        <Link href={`/projects/${projectId}`} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--fg-muted)] hover:text-[var(--fg-default)]">
          <ArrowLeft className="h-4 w-4" />
          Back to project
        </Link>
        <EmptyState
          icon={<Layers className="h-12 w-12" />}
          title="No composition available"
          description="Build a composition from your project assets to start editing the timeline."
          action={
            <div className="flex items-center gap-2">
              <Select value={exportPreset} onChange={(e) => setExportPreset(e.target.value)}>
                {exportPresets.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </Select>
              <Button onClick={handleBuild} disabled={buildComposition.isPending}>
                {buildComposition.isPending ? 'Building...' : 'Build composition'}
              </Button>
            </div>
          }
        />
      </div>
    )
  }

  const tracks = composition.timeline.tracks
  const totalDuration = composition.total_duration

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
            <h1 className="text-xl font-bold text-[var(--fg-default)]">Timeline Editor</h1>
            <p className="text-sm text-[var(--fg-muted)]">
              Version {composition.version} · {composition.track_count} tracks · {totalDuration.toFixed(1)}s · {composition.export_profile.resolution}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePreview}
            disabled={generatePreview.isPending}
          >
            <Eye className="mr-2 h-3.5 w-3.5" />
            {generatePreview.isPending ? 'Generating...' : 'Preview'}
          </Button>
          <Button variant="outline" size="sm" onClick={handleBuild}>
            <RefreshCw className="mr-2 h-3.5 w-3.5" />
            Rebuild
          </Button>
        </div>
      </div>

      {/* Validation status */}
      <Card>
        <CardContent className="flex items-center gap-3 py-3">
          {composition.is_valid ? (
            <>
              <CheckCircle2 className="h-5 w-5 text-[var(--status-success)]" />
              <span className="text-sm text-[var(--fg-default)]">Composition validated — ready for rendering</span>
            </>
          ) : (
            <>
              <AlertCircle className="h-5 w-5 text-[var(--status-error)]" />
              <span className="text-sm text-[var(--fg-default)]">Composition has validation issues</span>
            </>
          )}
          <Badge variant="outline" className="ml-auto">
            <Gauge className="mr-1 h-3 w-3" />
            {composition.export_profile.fps} FPS
          </Badge>
          <Badge variant="outline">
            {composition.export_profile.codec}
          </Badge>
        </CardContent>
      </Card>

      {/* Scene overview */}
      {composition.scenes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Scenes</CardTitle>
            <CardDescription>{composition.scene_count} scenes in this composition</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {composition.scenes.map((scene) => (
                <div
                  key={scene.id}
                  className="rounded-lg border border-[var(--border-default)] p-3 text-sm"
                  style={{ minWidth: '160px' }}
                >
                  <div className="font-medium text-[var(--fg-default)]">Scene {scene.scene_number}</div>
                  <div className="mt-1 text-xs text-[var(--fg-muted)]">
                    <Clock className="mr-1 inline h-3 w-3" />
                    {scene.start_time.toFixed(1)}s - {(scene.start_time + scene.duration).toFixed(1)}s
                  </div>
                  <div className="mt-1 line-clamp-2 text-xs text-[var(--fg-muted)]">
                    {scene.visual_description || scene.narration}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Timeline tracks */}
      <Card>
        <CardHeader>
          <CardTitle>Timeline</CardTitle>
          <CardDescription>
            {tracks.length} tracks · {totalDuration.toFixed(1)}s total duration
          </CardDescription>
        </CardHeader>
        <CardContent>
          {tracks.length > 0 ? (
            <div className="space-y-2">
              {/* Time ruler */}
              <div className="flex items-center border-b border-[var(--border-default)] pb-1 text-xs text-[var(--fg-muted)]">
                <div className="w-32 shrink-0">Track</div>
                <div className="flex-1 relative h-5">
                  {Array.from({ length: Math.ceil(totalDuration / 5) + 1 }, (_, i) => (
                    <div
                      key={i}
                      className="absolute top-0 border-l border-[var(--border-default)] pl-1"
                      style={{ left: `${(i * 5 / totalDuration) * 100}%` }}
                    >
                      {i * 5}s
                    </div>
                  ))}
                </div>
              </div>

              {/* Tracks */}
              {tracks.map((track: TrackDTO) => {
                const config = trackTypeConfig[track.track_type] ?? trackTypeConfig.custom
                const TrackIcon = config.icon
                return (
                  <div
                    key={track.id}
                    className={`flex items-center rounded-lg border p-2 transition-colors hover:bg-[var(--bg-surface-hover)] ${
                      selectedTrack === track.id ? 'border-[var(--fg-default)]' : 'border-[var(--border-default)]'
                    }`}
                    onClick={() => setSelectedTrack(track.id)}
                  >
                    {/* Track label */}
                    <div className="w-32 shrink-0">
                      <div className="flex items-center gap-2">
                        <TrackIcon className="h-4 w-4" style={{ color: config.color }} />
                        <span className="text-xs font-medium text-[var(--fg-default)]">{config.label}</span>
                      </div>
                      <div className="mt-0.5 flex gap-1">
                        {track.muted && <Badge variant="secondary" className="text-xs">Muted</Badge>}
                        {track.locked && <Badge variant="secondary" className="text-xs">Locked</Badge>}
                        {!track.visible && <Badge variant="secondary" className="text-xs">Hidden</Badge>}
                      </div>
                    </div>

                    {/* Clips */}
                    <div className="flex-1 relative h-12 rounded bg-[var(--bg-surface)]">
                      {track.clips.map((clip) => {
                        const left = (clip.start_time / totalDuration) * 100
                        const width = (clip.duration / totalDuration) * 100
                        return (
                          <div
                            key={clip.id}
                            className="absolute top-1 bottom-1 rounded border px-1 text-xs overflow-hidden"
                            style={{
                              left: `${left}%`,
                              width: `${Math.max(width, 2)}%`,
                              backgroundColor: config.color + '20',
                              borderColor: config.color + '60',
                            }}
                            title={`${clip.asset_type} · ${clip.duration.toFixed(1)}s`}
                          >
                            <div className="truncate text-[var(--fg-default)]">
                              {clip.asset_type}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <EmptyState
              icon={<Layers className="h-12 w-12" />}
              title="No tracks in timeline"
              description="The composition has no tracks. Try rebuilding the composition."
            />
          )}
        </CardContent>
      </Card>

      {/* Export profile */}
      <Card>
        <CardHeader>
          <CardTitle>Export profile</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div>
              <div className="text-xs text-[var(--fg-muted)]">Format</div>
              <div className="text-sm font-medium text-[var(--fg-default)] uppercase">{composition.export_profile.format}</div>
            </div>
            <div>
              <div className="text-xs text-[var(--fg-muted)]">Resolution</div>
              <div className="text-sm font-medium text-[var(--fg-default)]">{composition.export_profile.resolution}</div>
            </div>
            <div>
              <div className="text-xs text-[var(--fg-muted)]">Codec</div>
              <div className="text-sm font-medium text-[var(--fg-default)]">{composition.export_profile.codec}</div>
            </div>
            <div>
              <div className="text-xs text-[var(--fg-muted)]">Bitrate</div>
              <div className="text-sm font-medium text-[var(--fg-default)]">{composition.export_profile.video_bitrate}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex justify-between">
        <Link href={`/projects/${projectId}/generation`}>
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to generation
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/rendering`}>
          <Button>
            Continue to rendering
          </Button>
        </Link>
      </div>
    </div>
  )
}
