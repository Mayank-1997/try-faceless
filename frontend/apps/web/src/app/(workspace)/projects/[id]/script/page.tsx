'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useState } from 'react'
import { useScript, useScriptVersions, useCreateScript } from '@ai-video-studio/platform-sdk'
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
} from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import {
  ArrowLeft,
  FileText,
  RefreshCw,
  Download,
  Clock,
  Languages,
} from '@ai-video-studio/icons'
import { formatRelativeTime } from '@ai-video-studio/shared-utils'

export default function ScriptPage() {
  const params = useParams()
  const projectId = params.id as string
  const { addToast } = useToast()
  const [showVersions, setShowVersions] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({ hook: '', body: '', cta: '', language: 'en' })

  const { data: script, isLoading, error, refetch } = useScript(projectId)
  const { data: versions } = useScriptVersions(projectId)
  const createScript = useCreateScript()

  const handleRegenerate = () => {
    addToast({ title: 'Script regeneration started', variant: 'info' })
    refetch()
  }

  const handleSave = () => {
    createScript.mutate(
      { projectId, data: editForm },
      {
        onSuccess: () => {
          addToast({ title: 'Script saved', variant: 'success' })
          setEditMode(false)
        },
        onError: () => {
          addToast({ title: 'Failed to save script', variant: 'error' })
        },
      }
    )
  }

  const handleExport = () => {
    if (!script) return
    const content = `${script.hook}\n\n${script.body}\n\n${script.cta}`
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `script-v${script.version}.txt`
    a.click()
    URL.revokeObjectURL(url)
    addToast({ title: 'Script exported', variant: 'success' })
  }

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (error || !script) {
    return (
      <div className="p-6">
        <Link href={`/projects/${projectId}`} className="mb-4 inline-flex items-center gap-2 text-sm text-[var(--fg-muted)] hover:text-[var(--fg-default)]">
          <ArrowLeft className="h-4 w-4" />
          Back to project
        </Link>
        <EmptyState
          icon={<FileText className="h-12 w-12" />}
          title="No script available"
          description="The workflow needs to reach the scripting step to generate a script."
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
            <h1 className="text-xl font-bold text-[var(--fg-default)]">Script</h1>
            <p className="text-sm text-[var(--fg-muted)]">
              Version {script.version} · {script.word_count} words · ~{script.estimated_duration_seconds}s
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="mr-2 h-3.5 w-3.5" />
            Export
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowVersions(!showVersions)}
          >
            {showVersions ? 'Hide versions' : `Versions (${versions?.length ?? 0})`}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setEditForm({ hook: script.hook, body: script.body, cta: script.cta, language: script.language })
              setEditMode(true)
            }}
          >
            Edit
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
            <CardTitle>Script versions</CardTitle>
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
                      {v.word_count} words · {formatRelativeTime(v.updated_at)}
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

      {/* Edit mode */}
      {editMode ? (
        <Card>
          <CardHeader>
            <CardTitle>Edit script</CardTitle>
            <CardDescription>Create a new version with your edits</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium">Hook</label>
                <Input
                  value={editForm.hook}
                  onChange={(e) => setEditForm((f) => ({ ...f, hook: e.target.value }))}
                  placeholder="Opening hook to grab attention..."
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Body</label>
                <Textarea
                  value={editForm.body}
                  onChange={(e) => setEditForm((f) => ({ ...f, body: e.target.value }))}
                  rows={16}
                  placeholder="Main script content..."
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Call to action</label>
                <Input
                  value={editForm.cta}
                  onChange={(e) => setEditForm((f) => ({ ...f, cta: e.target.value }))}
                  placeholder="Closing call to action..."
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Language</label>
                <Input
                  value={editForm.language}
                  onChange={(e) => setEditForm((f) => ({ ...f, language: e.target.value }))}
                  placeholder="en"
                  className="w-20"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setEditMode(false)}>Cancel</Button>
                <Button onClick={handleSave} disabled={createScript.isPending}>
                  {createScript.isPending ? 'Saving...' : 'Save new version'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Script stats */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardContent className="flex items-center gap-3 py-4">
                <FileText className="h-8 w-8 text-[var(--fg-muted)]" />
                <div>
                  <div className="text-2xl font-bold text-[var(--fg-default)]">{script.word_count}</div>
                  <div className="text-xs text-[var(--fg-muted)]">Words</div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-center gap-3 py-4">
                <Clock className="h-8 w-8 text-[var(--fg-muted)]" />
                <div>
                  <div className="text-2xl font-bold text-[var(--fg-default)]">
                    {Math.floor(script.estimated_duration_seconds / 60)}m {script.estimated_duration_seconds % 60}s
                  </div>
                  <div className="text-xs text-[var(--fg-muted)]">Est. duration</div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex items-center gap-3 py-4">
                <Languages className="h-8 w-8 text-[var(--fg-muted)]" />
                <div>
                  <div className="text-2xl font-bold text-[var(--fg-default)]">{script.language}</div>
                  <div className="text-xs text-[var(--fg-muted)]">Language</div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Script content */}
          {script.hook && (
            <Card>
              <CardHeader>
                <CardTitle>Hook</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-[var(--fg-default)]">{script.hook}</p>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Body</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--fg-default)]">
                {script.body}
              </div>
            </CardContent>
          </Card>

          {script.cta && (
            <Card>
              <CardHeader>
                <CardTitle>Call to action</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-[var(--fg-default)]">{script.cta}</p>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Link href={`/projects/${projectId}/research`}>
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to research
          </Button>
        </Link>
        <Link href={`/projects/${projectId}/storyboard`}>
          <Button>
            Continue to storyboard
          </Button>
        </Link>
      </div>
    </div>
  )
}
