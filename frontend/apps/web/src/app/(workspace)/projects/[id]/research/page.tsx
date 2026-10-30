'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useResearch, useResearchVersions } from '@ai-video-studio/platform-sdk'
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
} from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import {
  ArrowLeft,
  BookOpen,
  RefreshCw,
  Tag,
  Globe,
  Users,
  Lightbulb,
  Quote,
  ListOrdered,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'
import { useState } from 'react'

export default function ResearchPage() {
  const params = useParams()
  const projectId = params.id as string
  const { addToast } = useToast()
  const [showVersions, setShowVersions] = useState(false)

  const { data: research, isLoading, error, refetch } = useResearch(projectId)
  const { data: versions } = useResearchVersions(projectId)

  const handleRegenerate = () => {
    addToast({ title: 'Research regeneration started', variant: 'info' })
    refetch()
  }

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (error || !research) {
    return (
      <div className="p-6">
        <Link href={`/projects/${projectId}`} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--fg-muted)] hover:text-[var(--fg-default)]">
          <ArrowLeft className="h-4 w-4" />
          Back to project
        </Link>
        <EmptyState
          icon={<BookOpen className="h-12 w-12" />}
          title="No research available"
          description="Start the workflow to generate research for this project."
          action={
            <Link href={`/projects/${projectId}`}>
              <Button>Go to project</Button>
            </Link>
          }
        />
      </div>
    )
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
            <h1 className="text-xl font-bold text-[var(--fg-default)]">Research</h1>
            <p className="text-sm text-[var(--fg-muted)]">
              Version {research.version} · Updated {formatRelativeTime(research.updated_at)}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowVersions(!showVersions)}
          >
            {showVersions ? 'Hide versions' : `View versions (${versions?.length ?? 0})`}
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
            <CardTitle>Research versions</CardTitle>
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
                      {formatRelativeTime(v.updated_at)}
                    </span>
                  </div>
                  <Badge variant={v.status === 'completed' ? 'success' : 'secondary'}>
                    {v.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Summary</CardTitle>
          <CardDescription>AI-generated research summary for this topic</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-[var(--fg-default)]">{research.summary}</p>
        </CardContent>
      </Card>

      {/* Keywords & Audience */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Tag className="h-4 w-4" />
              Keywords
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {research.keywords.map((kw, i) => (
                <Badge key={i} variant="secondary">{kw}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Audience pain points
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5">
              {research.audience_pain_points.map((point, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-[var(--fg-default)]">
                  <span className="mt-1 text-[var(--fg-muted)]">•</span>
                  {point}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Timeline */}
      {research.timeline.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ListOrdered className="h-4 w-4" />
              Timeline
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-2">
              {research.timeline.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-[var(--fg-default)]">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--bg-surface-hover)] text-xs font-medium">
                    {i + 1}
                  </span>
                  {item}
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      {/* Interesting facts */}
      {research.interesting_facts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4" />
              Interesting facts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {research.interesting_facts.map((fact, i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-[var(--fg-default)]">
                  <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--fg-muted)]" />
                  {fact}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sources */}
      {research.sources.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              Sources
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              {research.sources.map((src, i) => (
                <a
                  key={i}
                  href={src}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block truncate text-sm text-[var(--accent)] hover:underline"
                >
                  {src}
                </a>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Navigation to next step */}
      <div className="flex justify-between">
        <Link href={`/projects/${projectId}`}>
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to project
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/script`}>
          <Button>
            Continue to script
          </Button>
        </Link>
      </div>
    </div>
  )
}
