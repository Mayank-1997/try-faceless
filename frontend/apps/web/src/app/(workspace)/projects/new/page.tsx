'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useCreateProject } from '@ai-video-studio/platform-sdk'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  Button,
  Input,
  Textarea,
  Select,
  Badge,
  Progress,
} from '@ai-video-studio/design-system'
import { useToast } from '@ai-video-studio/design-system'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Video,
  FileText,
  Linkedin,
  Twitter,
  Instagram,
  Podcast,
  BookOpen,
  GraduationCap,
} from '@ai-video-studio/icons'
import { ContentType, VideoStyle } from '@ai-video-studio/shared-types'

const contentTypeOptions = [
  { value: ContentType.YOUTUBE_VIDEO, label: 'YouTube Video', icon: Video },
  { value: ContentType.BLOG, label: 'Blog Post', icon: FileText },
  { value: ContentType.LINKEDIN, label: 'LinkedIn Article', icon: Linkedin },
  { value: ContentType.TWITTER, label: 'Twitter Thread', icon: Twitter },
  { value: ContentType.INSTAGRAM, label: 'Instagram Post', icon: Instagram },
  { value: ContentType.PODCAST, label: 'Podcast', icon: Podcast },
  { value: ContentType.DOCUMENTATION, label: 'Documentation', icon: BookOpen },
  { value: ContentType.COURSE, label: 'Course', icon: GraduationCap },
]

const videoStyleOptions = [
  { value: VideoStyle.CINEMATIC, label: 'Cinematic' },
  { value: VideoStyle.DOCUMENTARY, label: 'Documentary' },
  { value: VideoStyle.EXPLAINER, label: 'Explainer' },
  { value: VideoStyle.TALKING_HEAD, label: 'Talking Head' },
  { value: VideoStyle.ANIMATED, label: 'Animated' },
  { value: VideoStyle.MIXED, label: 'Mixed' },
  { value: VideoStyle.STOCK_FOOTAGE, label: 'Stock Footage' },
  { value: VideoStyle.WHITEBOARD, label: 'Whiteboard' },
]

const aspectRatioOptions = [
  { value: '16:9', label: '16:9 Landscape (1920×1080)' },
  { value: '9:16', label: '9:16 Portrait (1080×1920) — Shorts/Reels' },
]

const steps = ['Content Type', 'Details', 'Review']

const beat1Sections = [
  {
    key: 'scene',
    label: 'Scene',
    required: true,
    placeholder:
      'Location, environment and weather — e.g. a sheer rocky cliff 150–200m above a dark fjord, snow-covered mountains, heavy rain.',
  },
  {
    key: 'camera',
    label: 'Camera',
    required: true,
    placeholder:
      'Camera type, position and movement — e.g. close third-person chase camera ~2m behind the diver, follows him downward.',
  },
  {
    key: 'action',
    label: 'Action',
    required: true,
    placeholder:
      'What the subject does, in order — e.g. he takes two running steps, launches into a forward dive, arms extended.',
  },
  {
    key: 'ending',
    label: 'Ending (optional)',
    required: false,
    placeholder:
      'Where the clip should end — e.g. just above the water, a split second before impact. Leave blank to let the model decide the natural stopping point.',
  },
  {
    key: 'visual_style',
    label: 'Visual style (optional)',
    required: false,
    placeholder: 'Photorealistic live-action, natural motion blur, real-time speed — not slow motion.',
  },
  {
    key: 'audio',
    label: 'Audio (optional)',
    required: false,
    placeholder: 'Rushing wind, rain, distant thunder — no music, no narration, no text.',
  },
  {
    key: 'continuity',
    label: 'Continuity (optional)',
    required: false,
    placeholder: 'What must stay identical — same diver, outfit, cliff, fjord, weather.',
  },
  {
    key: 'avoid',
    label: 'Avoid in this clip (optional)',
    required: false,
    placeholder: 'Camera cuts, drone shots, front-facing views, floating, slow motion...',
  },
] as const

const beat1RequiredKeys = beat1Sections.filter((s) => s.required).map((s) => s.key)

// Mirrors the backend video provider (NEXT_PUBLIC_VIDEO_PROVIDER in docker-compose).
// Kling generates up to 15s per call and chains via last-frame image-to-video;
// Veo generates one 8s clip then 7s server-side extensions.
const VIDEO_PROVIDER = process.env.NEXT_PUBLIC_VIDEO_PROVIDER === 'kling' ? 'kling' : 'veo'
const SEGMENT_SECONDS = VIDEO_PROVIDER === 'kling' ? 15 : 7

function composeBeat1(sections: Record<string, string>): string {
  return beat1Sections
    .map((s) => {
      const text = (sections[s.key] ?? '').trim()
      return text ? `${s.label.replace(/ \(optional\)$/, '').toUpperCase()}:\n${text}` : ''
    })
    .filter(Boolean)
    .join('\n\n')
}

export default function NewProjectPage() {
  const router = useRouter()
  const { addToast } = useToast()
  const createMutation = useCreateProject({
    onSuccess: (project) => {
      addToast({ title: 'Project created', variant: 'success' })
      router.push(`/projects/${project.id}`)
    },
    onError: (err) => {
      addToast({ title: 'Failed to create project', description: err.message, variant: 'error' })
    },
  })

  const [step, setStep] = useState(0)
  const [form, setForm] = useState({
    title: '',
    description: '',
    language: 'en',
    content_type: ContentType.YOUTUBE_VIDEO,
    video_style: VideoStyle.MIXED,
    target_duration_seconds: '',
    aspect_ratio: '16:9',
    production_mode: 'explainer',
    visual_anchor: '',
    clip_beats: [''] as string[],
    beat1_sections: Object.fromEntries(beat1Sections.map((s) => [s.key, ''])) as Record<
      string,
      string
    >,
    avoid: '',
    narration_text: '',
  })

  const update = (key: string, value: string) => setForm((prev) => ({ ...prev, [key]: value }))

  const setBeatCount = (count: number) =>
    setForm((prev) => ({
      ...prev,
      clip_beats: Array.from({ length: count }, (_, i) => prev.clip_beats[i] ?? ''),
    }))

  const setBeat = (index: number, value: string) =>
    setForm((prev) => {
      const clip_beats = [...prev.clip_beats]
      clip_beats[index] = value
      return { ...prev, clip_beats }
    })

  const setBeat1Section = (key: string, value: string) =>
    setForm((prev) => ({
      ...prev,
      beat1_sections: { ...prev.beat1_sections, [key]: value },
    }))
  const directClipCount =
    VIDEO_PROVIDER === 'kling'
      ? Math.max(1, Math.ceil(Number(form.target_duration_seconds) / 15))
      : Number(form.target_duration_seconds) <= 8
        ? 1
        : 1 + Math.ceil((Number(form.target_duration_seconds) - 8) / 7)
  const clipCount =
    form.production_mode === 'direct_cinematic'
      ? directClipCount
      : Math.ceil((2 * Math.ceil(Number(form.target_duration_seconds) / 2)) / 8)

  const canProceed = () => {
    if (step === 0) return !!form.content_type
    if (step === 1)
      return (
        form.title.trim().length > 0 &&
        (form.production_mode !== 'direct_cinematic' ||
          (!!form.description.trim() &&
            !!form.visual_anchor.trim() &&
            !!form.target_duration_seconds &&
            Number(form.target_duration_seconds) >= 4 &&
            Number(form.target_duration_seconds) <= 120 &&
            form.clip_beats.length === clipCount &&
            form.clip_beats.every((beat, i) =>
              i === 0
                ? beat1RequiredKeys.every(
                    (key) => (form.beat1_sections[key] ?? '').trim().length > 0
                  )
                : beat.trim().length > 0
            ) &&
            form.narration_text.trim().split(/\s+/).filter(Boolean).length <=
              Number(form.target_duration_seconds) * 2))
      )
    return true
  }

  const handleCreate = () => {
    createMutation.mutate({
      title: form.title,
      description: form.description,
      language: form.language,
      audience: '',
      content_type: form.content_type,
      video_style: form.video_style,
      target_duration_seconds: form.target_duration_seconds
        ? parseInt(form.target_duration_seconds)
        : null,
      aspect_ratio: form.aspect_ratio,
      production_mode: form.production_mode as 'explainer' | 'direct_cinematic',
      visual_anchor: form.production_mode === 'direct_cinematic' ? form.visual_anchor : '',
      clip_beats:
        form.production_mode === 'direct_cinematic'
          ? form.clip_beats
              .map((beat, i) => (i === 0 ? composeBeat1(form.beat1_sections) : beat.trim()))
              .filter(Boolean)
          : [],
      avoid: form.production_mode === 'direct_cinematic' ? form.avoid : '',
      narration_text: form.production_mode === 'direct_cinematic' ? form.narration_text : '',
      tags: [],
    })
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--fg-default)]">Create New Project</h1>
        <p className="text-sm text-[var(--fg-muted)]">Set up your AI content generation project</p>
      </div>

      {/* Progress */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-[var(--fg-muted)]">
          {steps.map((s, i) => (
            <span key={s} className={i <= step ? 'font-medium text-[var(--brand-default)]' : ''}>
              {i + 1}. {s}
            </span>
          ))}
        </div>
        <Progress value={((step + 1) / steps.length) * 100} />
      </div>

      {/* Step 0: Content Type */}
      {step === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Choose Content Type</CardTitle>
            <CardDescription>What type of content do you want to create?</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {contentTypeOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => update('content_type', opt.value)}
                  className={`flex flex-col items-center gap-2 rounded-lg border p-4 transition-all ${
                    form.content_type === opt.value
                      ? 'border-[var(--brand-default)] bg-[var(--brand-subtle)]'
                      : 'border-[var(--border-default)] hover:border-[var(--brand-default)]'
                  }`}
                >
                  <opt.icon className="h-6 w-6 text-[var(--fg-default)]" />
                  <span className="text-xs font-medium text-[var(--fg-default)]">{opt.label}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 1: Details */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Project Details</CardTitle>
            <CardDescription>Tell us about your project</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                Title <span className="text-[var(--status-error)]">*</span>
              </label>
              <Input
                value={form.title}
                onChange={(e) => update('title', e.target.value)}
                placeholder="My Awesome Video"
                maxLength={300}
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                Description
              </label>
              <Textarea
                value={form.description}
                onChange={(e) => update('description', e.target.value)}
                placeholder="Describe what this project is about..."
                rows={3}
              />
            </div>

            {form.content_type === ContentType.YOUTUBE_VIDEO && (
              <div className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                    Production Flow
                  </label>
                  <Select
                    value={form.production_mode}
                    onChange={(e) => update('production_mode', e.target.value)}
                  >
                    <option value="explainer">Narrated explainer (research and script)</option>
                    <option value="direct_cinematic">
                      Direct cinematic video (follow my description)
                    </option>
                  </Select>
                </div>
                {form.production_mode === 'direct_cinematic' && (
                  <div className="space-y-4">
                    <p className="text-sm text-[var(--fg-muted)]">
                      Your description sets the scene, style and audio — keep the action sequence
                      out of it; each beat below directs one generated clip.{' '}
                      {VIDEO_PROVIDER === 'kling'
                        ? 'Direct cinematic uses Kling v3 via fal.ai — one clip of up to 15 seconds per beat; longer videos chain onto the last frame. For example, 15 seconds requires 1 beat and 30 seconds requires 2 beats.'
                        : 'Direct cinematic uses one initial 8-second Veo clip and then 7-second video extensions; for example, 15 seconds requires 2 beats and 30 seconds requires 5 beats.'}{' '}
                      Later beats continue the previous clip and the final result is trimmed to the
                      requested duration. Narration is optional; without it the generated clip audio
                      is retained.
                    </p>
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                        Fixed subject and setting *
                      </label>
                      <Textarea
                        value={form.visual_anchor}
                        onChange={(e) => update('visual_anchor', e.target.value)}
                        rows={3}
                        placeholder="Blonde woman in white athletic clothes; daylight jungle sinkhole; tiny trampoline on the floor below. Same character, place and outfit throughout."
                      />
                    </div>
                    <div className="space-y-3">
                      <div>
                        <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                          Number of clip beats *
                        </label>
                        <Select
                          value={String(form.clip_beats.length)}
                          onChange={(e) => setBeatCount(Number(e.target.value))}
                        >
                          {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                            <option key={n} value={n}>
                              {n}
                            </option>
                          ))}
                        </Select>
                      </div>
                      {form.clip_beats.length !== clipCount && form.target_duration_seconds && (
                        <p className="text-sm text-[var(--status-error)]">
                          {form.clip_beats.length} beat{form.clip_beats.length > 1 ? 's' : ''} needs
                          a duration of{' '}
                          {VIDEO_PROVIDER === 'kling'
                            ? `4–${15 * form.clip_beats.length}`
                            : form.clip_beats.length === 1
                              ? '4–8'
                              : `${7 * form.clip_beats.length - 5}–${7 * form.clip_beats.length + 1}`}
                          s, but {form.target_duration_seconds}s requires {clipCount} beat
                          {clipCount > 1 ? 's' : ''}.
                        </p>
                      )}
                      {form.clip_beats.map((beat, i) =>
                        i === 0 ? (
                          <div key={i} className="space-y-3 rounded-lg border border-[var(--border-default)] p-4">
                            <p className="text-sm font-medium text-[var(--fg-default)]">
                              Beat 1 — initial {VIDEO_PROVIDER === 'kling' ? '3–15-second' : '8-second'} clip *
                            </p>
                            <p className="text-xs text-[var(--fg-muted)]">
                              Structured sections produced the most reliable first clip. Fill the
                              required ones; empty optional sections are omitted from the prompt.
                            </p>
                            {beat1Sections.map((section) => (
                              <div key={section.key}>
                                <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                                  {section.label}
                                  {section.required && (
                                    <span className="text-[var(--status-error)]"> *</span>
                                  )}
                                </label>
                                <Textarea
                                  value={form.beat1_sections[section.key] ?? ''}
                                  onChange={(e) => setBeat1Section(section.key, e.target.value)}
                                  rows={2}
                                  maxLength={100000}
                                  placeholder={section.placeholder}
                                />
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div key={i}>
                            <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                              Beat {i + 1} — extension {i} ({SEGMENT_SECONDS} seconds) *
                            </label>
                            <Textarea
                              value={beat}
                              onChange={(e) => setBeat(i, e.target.value)}
                              rows={3}
                              maxLength={100000}
                              placeholder="Extension action: continue smoothly from the last frame — what happens next in the same continuous shot."
                            />
                          </div>
                        )
                      )}
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                        Avoid (optional)
                      </label>
                      <Input
                        value={form.avoid}
                        onChange={(e) => update('avoid', e.target.value)}
                        placeholder="No harness, cables, cliff-mounted rig or extra characters"
                      />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                        Narration (optional)
                      </label>
                      <Textarea
                        value={form.narration_text}
                        onChange={(e) => update('narration_text', e.target.value)}
                        rows={2}
                        placeholder="Leave blank for no voiceover or subtitles"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                  Language
                </label>
                <Select value={form.language} onChange={(e) => update('language', e.target.value)}>
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="hi">Hindi</option>
                  <option value="zh">Chinese</option>
                  <option value="ja">Japanese</option>
                </Select>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                  Target Duration (sec)
                </label>
                <Input
                  type="number"
                  value={form.target_duration_seconds}
                  onChange={(e) => update('target_duration_seconds', e.target.value)}
                  placeholder="e.g. 600"
                  min={1}
                  max={86400}
                />
              </div>
            </div>

            {form.content_type === ContentType.YOUTUBE_VIDEO && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                    Video Style
                  </label>
                  <Select
                    value={form.video_style}
                    onChange={(e) => update('video_style', e.target.value)}
                  >
                    {videoStyleOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-[var(--fg-default)]">
                    Aspect Ratio
                  </label>
                  <Select
                    value={form.aspect_ratio}
                    onChange={(e) => update('aspect_ratio', e.target.value)}
                  >
                    {aspectRatioOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </Select>
                </div>
              </div>
            )}

          </CardContent>
        </Card>
      )}

      {/* Step 2: Review */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Review & Create</CardTitle>
            <CardDescription>Confirm your project settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-[var(--fg-muted)]">Content Type</span>
              <Badge variant="info">
                {contentTypeOptions.find((o) => o.value === form.content_type)?.label}
              </Badge>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-[var(--fg-muted)]">Title</span>
              <span className="font-medium text-[var(--fg-default)]">{form.title}</span>
            </div>
            {form.description && (
              <div className="flex justify-between text-sm">
                <span className="text-[var(--fg-muted)]">Description</span>
                <span className="max-w-[60%] truncate text-[var(--fg-default)]">
                  {form.description}
                </span>
              </div>
            )}
            <div className="flex justify-between text-sm">
              <span className="text-[var(--fg-muted)]">Language</span>
              <span className="text-[var(--fg-default)]">{form.language}</span>
            </div>
            {form.content_type === ContentType.YOUTUBE_VIDEO && (
              <div className="flex justify-between text-sm">
                <span className="text-[var(--fg-muted)]">Production Flow</span>
                <span className="text-[var(--fg-default)]">
                  {form.production_mode === 'direct_cinematic'
                    ? 'Direct cinematic video'
                    : 'Narrated explainer'}
                </span>
              </div>
            )}
            {form.content_type === ContentType.YOUTUBE_VIDEO && (
              <div className="flex justify-between text-sm">
                <span className="text-[var(--fg-muted)]">Video Style</span>
                <span className="text-[var(--fg-default)]">
                  {videoStyleOptions.find((o) => o.value === form.video_style)?.label}
                </span>
              </div>
            )}
            {form.content_type === ContentType.YOUTUBE_VIDEO && (
              <div className="flex justify-between text-sm">
                <span className="text-[var(--fg-muted)]">Aspect Ratio</span>
                <span className="text-[var(--fg-default)]">
                  {aspectRatioOptions.find((o) => o.value === form.aspect_ratio)?.label}
                </span>
              </div>
            )}
            {form.target_duration_seconds && (
              <div className="flex justify-between text-sm">
                <span className="text-[var(--fg-muted)]">Target Duration</span>
                <span className="text-[var(--fg-default)]">{form.target_duration_seconds}s</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={() => (step === 0 ? router.push('/projects') : setStep(step - 1))}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          {step === 0 ? 'Cancel' : 'Back'}
        </Button>

        {step < steps.length - 1 ? (
          <Button onClick={() => setStep(step + 1)} disabled={!canProceed()}>
            Next
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleCreate} disabled={createMutation.isPending}>
            <Check className="mr-2 h-4 w-4" />
            {createMutation.isPending ? 'Creating...' : 'Create Project'}
          </Button>
        )}
      </div>
    </div>
  )
}
