'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useState } from 'react'
import { useAssets } from '@ai-video-studio/platform-sdk'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Button,
  Badge,
  Skeleton,
  EmptyState,
  Select,
} from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import {
  ArrowLeft,
  Image,
  Video,
  Music,
  Mic,
  FileText,
  Download,
  RefreshCw,
  Eye,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import type { AssetType } from '@ai-video-studio/shared-types'

const assetTypeFilters: { value: string; label: string; icon: typeof Image }[] = [
  { value: 'image', label: 'Images', icon: Image },
  { value: 'video', label: 'Videos', icon: Video },
  { value: 'voice', label: 'Voice', icon: Mic },
  { value: 'music', label: 'Music', icon: Music },
  { value: 'subtitle', label: 'Subtitles', icon: FileText },
  { value: 'thumbnail', label: 'Thumbnails', icon: Image },
]

const assetTypeIcon: Record<string, typeof Image> = {
  image: Image,
  video: Video,
  voice: Mic,
  music: Music,
  subtitle: FileText,
  thumbnail: Image,
}

export default function AssetsPage() {
  const params = useParams()
  const projectId = params.id as string
  const { addToast } = useToast()
  const [filter, setFilter] = useState<string>('')

  const { data: assetsData, isLoading, error } = useAssets(projectId, filter ? { asset_type: filter } : undefined)

  const handleDownload = (storageRef: string, filename: string) => {
    addToast({ title: `Downloading ${filename}...`, variant: 'info' })
  }

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-12 w-full" />
        <div className="grid gap-4 md:grid-cols-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
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
          icon={<Image className="h-12 w-12" />}
          title="Failed to load assets"
          description="There was an error loading the assets for this project."
        />
      </div>
    )
  }

  const assets = assetsData?.items ?? []

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
            <h1 className="text-xl font-bold text-[var(--fg-default)]">Asset Studio</h1>
            <p className="text-sm text-[var(--fg-muted)]">
              {assetsData?.total ?? 0} assets · All generated media for this project
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => addToast({ title: 'Asset generation started', variant: 'info' })}>
          <RefreshCw className="mr-2 h-3.5 w-3.5" />
          Generate assets
        </Button>
      </div>

      {/* Filter tabs */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={!filter ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('')}
        >
          All ({assetsData?.total ?? 0})
        </Button>
        {assetTypeFilters.map((f) => {
          const Icon = f.icon
          return (
            <Button
              key={f.value}
              variant={filter === f.value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter(f.value)}
            >
              <Icon className="mr-2 h-3.5 w-3.5" />
              {f.label}
            </Button>
          )
        })}
      </div>

      {/* Asset grid */}
      {assets.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {assets.map((asset) => {
            const Icon = assetTypeIcon[asset.asset_type] ?? Image
            return (
              <Card key={asset.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4 text-[var(--fg-muted)]" />
                      <span className="text-sm font-medium capitalize">{asset.asset_type}</span>
                    </div>
                    <Badge variant={asset.generation_status === 'completed' ? 'success' : asset.generation_status === 'pending' ? 'secondary' : 'warning'}>
                      {asset.generation_status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  {/* Preview area */}
                  <div className="mb-3 flex h-32 items-center justify-center rounded-lg bg-[var(--bg-surface-hover)]">
                    {asset.asset_type === 'image' || asset.asset_type === 'thumbnail' ? (
                      <Image className="h-10 w-10 text-[var(--fg-muted)]" />
                    ) : asset.asset_type === 'video' ? (
                      <Video className="h-10 w-10 text-[var(--fg-muted)]" />
                    ) : asset.asset_type === 'voice' ? (
                      <Mic className="h-10 w-10 text-[var(--fg-muted)]" />
                    ) : asset.asset_type === 'music' ? (
                      <Music className="h-10 w-10 text-[var(--fg-muted)]" />
                    ) : (
                      <FileText className="h-10 w-10 text-[var(--fg-muted)]" />
                    )}
                  </div>

                  {/* Asset metadata */}
                  <div className="space-y-1 text-xs text-[var(--fg-muted)]">
                    <div>Provider: <span className="text-[var(--fg-default)]">{asset.provider}</span></div>
                    <div>Cost: <span className="text-[var(--fg-default)]">${asset.generation_cost_usd.toFixed(4)}</span></div>
                    <div>Generated: <span className="text-[var(--fg-default)]">{formatRelativeTime(asset.created_at)}</span></div>
                    {asset.quality_score !== null && (
                      <div>Quality: <span className="text-[var(--fg-default)]">{(asset.quality_score * 100).toFixed(0)}%</span></div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="mt-3 flex gap-1.5">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => addToast({ title: 'Preview not available yet', variant: 'info' })}
                    >
                      <Eye className="mr-1 h-3 w-3" />
                      Preview
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleDownload(asset.storage_ref, asset.id)}
                      disabled={asset.generation_status !== 'completed'}
                    >
                      <Download className="mr-1 h-3 w-3" />
                      Download
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : (
        <EmptyState
          icon={<Image className="h-12 w-12" />}
          title="No assets generated yet"
          description="Assets will appear here once the workflow reaches the asset generation step."
          action={
            <Button onClick={() => addToast({ title: 'Asset generation started', variant: 'info' })}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Generate assets
            </Button>
          }
        />
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Link href={`/projects/${projectId}/storyboard`}>
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to storyboard
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/generation`}>
          <Button>
            Continue to generation
          </Button>
        </Link>
      </div>
    </div>
  )
}
