// =============================================================================
// Business DTOs — matching backend src/application/dto/business_dtos.py
// =============================================================================

export interface CreateProjectRequest {
  title: string
  description?: string
  language?: string
  audience?: string
  content_type?: string
  video_style?: string
  target_duration_seconds?: number | null
  aspect_ratio?: string
  production_mode?: 'explainer' | 'direct_cinematic'
  visual_anchor?: string
  clip_beats?: string[]
  avoid?: string
  narration_text?: string
  tags?: string[]
  metadata?: Record<string, unknown>
}

export interface UpdateProjectRequest {
  title?: string
  description?: string
  language?: string
  audience?: string
  content_type?: string
  video_style?: string
  target_duration_seconds?: number | null
  tags?: string[]
  metadata?: Record<string, unknown>
}

export interface ProjectResponse {
  id: string
  owner_id: string
  title: string
  description: string
  language: string
  audience: string
  content_type: string
  video_style: string
  target_duration_seconds: number | null
  status: string
  current_step: string
  tags: string[]
  metadata: Record<string, unknown>
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface ProjectListResponse {
  items: ProjectResponse[]
  total: number
  offset: number
  limit: number
}

// =============================================================================
// Workflow DTOs
// =============================================================================

export interface WorkflowResponse {
  id: string
  project_id: string
  version: number
  current_step: string
  status: string
  started_at: string | null
  completed_at: string | null
  execution_time_seconds: number | null
  failure_reason: string | null
  retry_count: number
  checkpoint_ref: string | null
  created_at: string
  updated_at: string
}

// =============================================================================
// Research DTOs
// =============================================================================

export interface ResearchResponse {
  id: string
  project_id: string
  workflow_id: string | null
  summary: string
  timeline: string[]
  interesting_facts: string[]
  sources: string[]
  keywords: string[]
  references: string[]
  statistics: Record<string, unknown>
  audience_pain_points: string[]
  version: number
  status: string
  created_at: string
  updated_at: string
}

// =============================================================================
// Script DTOs
// =============================================================================

export interface CreateScriptRequest {
  hook?: string
  body: string
  cta?: string
  language?: string
}

export interface ScriptResponse {
  id: string
  project_id: string
  workflow_id: string | null
  hook: string
  body: string
  cta: string
  word_count: number
  estimated_duration_seconds: number
  version: number
  language: string
  status: string
  created_at: string
  updated_at: string
}

// =============================================================================
// Storyboard DTOs
// =============================================================================

export interface StoryboardResponse {
  id: string
  project_id: string
  workflow_id: string | null
  version: number
  scene_count: number
  estimated_duration_seconds: number
  style: string
  status: string
  narrative_structure: string
  pacing_notes: string
  package_json?: string
  created_at: string
  updated_at: string
}

// =============================================================================
// Scene DTOs
// =============================================================================

export interface SceneResponse {
  id: string
  project_id: string
  storyboard_id: string | null
  workflow_id: string | null
  scene_number: number
  title: string
  duration_seconds: number
  narration: string
  importance_score: number
  emotion: string
  visual_type: string
  camera_angle: string | null
  camera_motion: string | null
  lens: string | null
  lighting: string | null
  composition: string | null
  transition: string | null
  subtitle: string | null
  voice_timing: Record<string, unknown>
  background_music: string | null
  sound_effects: string[]
  generation_status: string
  review_status: string
  created_at: string
  updated_at: string
}

export interface SceneListResponse {
  items: SceneResponse[]
  total: number
}

// =============================================================================
// Asset DTOs
// =============================================================================

export interface AssetResponse {
  id: string
  project_id: string
  scene_id: string | null
  asset_type: string
  provider: string
  prompt_version: string
  generation_cost_usd: number
  generation_time_seconds: number
  generation_status: string
  storage_type: string
  storage_ref: string
  metadata: Record<string, unknown>
  quality_score: number | null
  created_at: string
  updated_at: string
}

export interface AssetListResponse {
  items: AssetResponse[]
  total: number
}

// =============================================================================
// Generation Job DTOs
// =============================================================================

export interface GenerationJobResponse {
  id: string
  project_id: string
  workflow_id: string | null
  scene_id: string | null
  job_type: string
  status: string
  priority: string
  payload: Record<string, unknown>
  result: Record<string, unknown>
  error_message: string | null
  retry_count: number
  max_retries: number
  queued_at: string
  started_at: string | null
  completed_at: string | null
  execution_time_seconds: number | null
  created_at: string
  updated_at: string
}

// =============================================================================
// Prompt Execution DTOs
// =============================================================================

export interface PromptExecutionResponse {
  id: string
  project_id: string | null
  workflow_id: string | null
  scene_id: string | null
  agent_type: string
  prompt_template: string
  prompt_variables: Record<string, unknown>
  rendered_prompt: string
  provider: string
  model: string
  temperature: number
  response: string
  latency_ms: number
  cost_usd: number
  input_tokens: number
  output_tokens: number
  cached_tokens: number
  status: string
  error_message: string | null
  created_at: string
}

// =============================================================================
// Analytics DTOs
// =============================================================================

export interface CostSummaryResponse {
  total_cost_usd: number
  cost_by_provider: Record<string, number>
  cost_by_category: Record<string, number>
}

export interface TokenUsageSummaryResponse {
  total_tokens: number
  tokens_by_provider: Record<string, number>
}

// =============================================================================
// Composition DTOs
// =============================================================================

export interface TimelineClipDTO {
  id: string
  track_id: string
  asset_uri: string
  asset_type: string
  start_time: number
  duration: number
  in_point: number
  out_point: number | null
  speed: number
  volume: number
  opacity: number
  position_x: number
  position_y: number
  scale: number
  rotation: number
  z_index: number
  metadata: Record<string, unknown>
}

export interface TrackDTO {
  id: string
  name: string
  track_type: string
  layer: number
  visible: boolean
  locked: boolean
  muted: boolean
  solo: boolean
  clips: TimelineClipDTO[]
  metadata: Record<string, unknown>
}

export interface TimelineDTO {
  tracks: TrackDTO[]
  total_duration: number
  fps: number
  width: number
  height: number
  metadata: Record<string, unknown>
}

export interface CompositionSceneDTO {
  id: string
  scene_number: number
  scene_id: string
  start_time: number
  duration: number
  narration: string
  visual_description: string
  camera_plan: Record<string, unknown>
  animation_plan: Record<string, unknown>
  asset_uris: Record<string, string>
  transitions: Record<string, unknown>[]
  metadata: Record<string, unknown>
}

export interface ExportProfileDTO {
  format: string
  resolution: string
  width: number
  height: number
  fps: number
  codec: string
  audio_codec: string
  video_bitrate: string
  audio_bitrate: string
  preset: string
  crf: number
  pixel_format: string
  hardware_acceleration: boolean
}

export interface CompositionDocumentDTO {
  id: string
  project_id: string
  version: number
  timeline: TimelineDTO
  scenes: CompositionSceneDTO[]
  export_profile: ExportProfileDTO
  total_duration: number
  scene_count: number
  track_count: number
  is_valid: boolean
  created_at: string
  metadata: Record<string, unknown>
}

export interface CreateCompositionRequest {
  project_id: string
  export_preset?: string
  resolution?: string
  fps?: number
}

export interface UpdateTimelineRequest {
  timeline: TimelineDTO
}

// =============================================================================
// Render DTOs
// =============================================================================

export interface RenderJobDTO {
  id: string
  composition_id: string
  project_id: string
  status: string
  priority: string
  output_path: string
  retry_count: number
  max_retries: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  error: string | null
  execution_time_seconds: number
  metadata: Record<string, unknown>
}

export interface RenderProgressDTO {
  job_id: string
  status: string
  progress_percentage: number
  current_stage: string
  stages_completed: string[]
  estimated_time_remaining: number
  frames_processed: number
  total_frames: number
}

export interface RenderMetricsDTO {
  render_time_seconds: number
  encoding_time_seconds: number
  total_frames: number
  dropped_frames: number
  average_fps: number
  peak_memory_mb: number
  cpu_usage: number
  gpu_usage: number
  output_size_bytes: number
  output_duration_seconds: number
  output_resolution: string
  output_fps: number
}

export interface QualityReportDTO {
  resolution_valid: boolean
  duration_valid: boolean
  subtitle_sync_valid: boolean
  audio_sync_valid: boolean
  no_dropped_frames: boolean
  all_assets_present: boolean
  encoding_success: boolean
  output_integrity: boolean
  overall_pass: boolean
  issues: string[]
}

export interface ProjectPackageDTO {
  id: string
  project_id: string
  composition_document: CompositionDocumentDTO
  final_video_path: string
  final_video_uri: string
  thumbnail_path: string
  thumbnail_uri: string
  subtitle_files: string[]
  is_complete: boolean
  render_report: RenderMetricsDTO
  quality_report: QualityReportDTO
  created_at: string
  version: number
}

export interface CreateRenderRequest {
  composition_id: string
  priority?: string
  output_path?: string
}

export interface PreviewResultDTO {
  preview_path: string
  preview_uri: string
  resolution: string
  duration_seconds: number
  file_size_bytes: number
}

// =============================================================================
// Publishing DTOs
// =============================================================================

export interface PublishingMetadataDTO {
  title: string
  description: string
  tags: string[]
  keywords: string[]
  category: string
  hashtags: string[]
  language: string
  privacy_status: string
  license: string
  made_for_kids: boolean
  embeddable: boolean
  public_stats_viewable: boolean
  notify_subscribers: boolean
  playlist_id: string | null
  recording_date: string | null
  recording_location: string | null
}

export interface PublishingTaskDTO {
  id: string
  plan_id: string
  platform: string
  mode: string
  metadata: PublishingMetadataDTO
  video_path: string
  thumbnail_path: string
  scheduled_at: string | null
  status: string
  priority: string
  retry_count: number
  max_retries: number
  error: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  execution_time_seconds: number
}

export interface PublishingPlanDTO {
  id: string
  project_id: string
  tasks: PublishingTaskDTO[]
  mode: string
  platform_count: number
  validation_errors: string[]
  validation_warnings: string[]
  created_at: string
}

export interface PublishingReportDTO {
  id: string
  plan_id: string
  project_id: string
  platform: string
  status: string
  video_url: string
  video_id: string
  upload_duration_seconds: number
  publish_duration_seconds: number
  total_duration_seconds: number
  warnings: string[]
  errors: string[]
  thumbnail_uploaded: boolean
  metadata_updated: boolean
  created_at: string
}

export interface PublishingJobDTO {
  id: string
  task_id: string
  project_id: string
  platform: string
  status: string
  priority: string
  scheduled_at: string | null
  retry_count: number
  max_retries: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  error: string | null
  execution_time_seconds: number
}

export interface PublishingProgressDTO {
  task_id: string
  status: string
  progress_percentage: number
  current_stage: string
  stages_completed: string[]
  upload_progress: number
  estimated_time_remaining: number
}

export interface CreatePublishingRequest {
  project_id: string
  platform: string
  mode: string
  metadata: Partial<PublishingMetadataDTO>
  scheduled_at?: string
}

export interface SchedulePublishRequest {
  scheduled_at: string
  timezone?: string
}

// ===========================================================================
// Phase 5 — Platform Experience DTOs
// ===========================================================================

// --- Analytics ---
export interface AnalyticsSummaryDTO {
  total_projects: number
  successful_projects: number
  failed_projects: number
  avg_generation_time: number
  avg_publishing_time: number
  avg_rendering_time: number
  success_rate: number
  failure_rate: number
  most_used_providers: Record<string, number>
  top_models: Record<string, number>
  project_growth: Array<{ date: string; count: number }>
  user_activity: Record<string, number>
}

export interface CostBreakdownDTO {
  cost_per_project: Record<string, number>
  cost_per_user: Record<string, number>
  cost_per_provider: Record<string, number>
  cost_per_asset: Record<string, number>
  cost_per_workflow: Record<string, number>
  daily_costs: Record<string, number>
  monthly_costs: Record<string, number>
  total_cost: number
  revenue: number
  profit_margin: number
}

// --- Usage ---
export interface UsageSummaryDTO {
  user_id: string
  org_id: string
  images_generated: number
  videos_generated: number
  voice_minutes: number
  rendering_minutes: number
  storage_bytes: number
  bandwidth_bytes: number
  projects_created: number
  publishing_count: number
  token_usage: number
  provider_usage: Record<string, number>
  period_start?: string
  period_end?: string
}

// --- Billing ---
export interface PlanFeaturesDTO {
  max_projects: number
  max_images_per_month: number
  max_videos_per_month: number
  max_voice_minutes_per_month: number
  max_rendering_minutes_per_month: number
  max_storage_gb: number
  max_bandwidth_gb: number
  max_team_members: number
  custom_branding: boolean
  priority_support: boolean
  api_access: boolean
  advanced_analytics: boolean
  white_label: boolean
  sso: boolean
}

export interface PlanDTO {
  id: string
  name: string
  plan_type: string
  price_monthly: number
  price_yearly: number
  currency: string
  features: PlanFeaturesDTO
  is_active: boolean
  description: string
}

export interface SubscriptionDTO {
  id: string
  user_id: string
  org_id: string
  plan_id: string
  plan_type: string
  status: string
  started_at: string
  current_period_start: string
  current_period_end?: string
  cancelled_at?: string
  trial_end?: string
}

export interface CreditBalanceDTO {
  user_id: string
  org_id: string
  credits: Record<string, number>
}

export interface InvoiceItemDTO {
  description: string
  quantity: number
  unit_price: number
  total: number
}

export interface InvoiceDTO {
  id: string
  user_id: string
  org_id: string
  subscription_id?: string
  status: string
  items: InvoiceItemDTO[]
  subtotal: number
  tax: number
  total: number
  currency: string
  issued_at: string
  due_at?: string
  paid_at?: string
}

export interface CreateSubscriptionRequest {
  plan_id: string
  trial_days?: number
}

export interface AddCreditsRequest {
  credit_type: string
  amount: number
}

// --- Organizations ---
export interface OrganizationDTO {
  id: string
  name: string
  slug: string
  owner_id: string
  plan_type: string
  member_count: number
  max_members: number
  is_active: boolean
  created_at: string
}

export interface TeamMemberDTO {
  id: string
  org_id: string
  user_id: string
  role: string
  joined_at: string
  invited_by: string
  is_active: boolean
}

export interface CreateOrganizationRequest {
  name: string
  slug?: string
  max_members?: number
}

// --- Feature Flags ---
export interface FeatureFlagDTO {
  key: string
  name: string
  description: string
  flag_type: string
  scope: string
  enabled: boolean
  percentage: number
  variants: Record<string, unknown>
  user_ids: string[]
  org_ids: string[]
  plan_types: string[]
  created_at: string
  updated_at?: string
}

export interface CreateFeatureFlagRequest {
  key: string
  name: string
  description?: string
  flag_type?: string
  scope?: string
  enabled?: boolean
  percentage?: number
}

// --- Admin ---
export interface PlatformOverviewDTO {
  timestamp: string
  analytics?: {
    total_projects: number
    success_rate: number
    failure_rate: number
    avg_generation_time: number
  }
  usage?: {
    total_records: number
  }
  billing?: {
    plans_available: number
    total_invoices: number
  }
  monitoring?: {
    latency_ms: number
    queue_size: number
    failure_count: number
    provider_availability: Record<string, number>
  }
  health?: {
    overall_status: string
    healthy_count: number
    degraded_count: number
    unhealthy_count: number
  }
  audit?: {
    total_entries: number
    actions: Record<string, number>
  }
}

export interface HealthReportDTO {
  overall_status: string
  checks: Array<{
    component: string
    status: string
    latency_ms: number
    message: string
  }>
  checked_at: string
}

export interface MonitoringSnapshotDTO {
  latency_ms: number
  queue_size: number
  worker_count: number
  active_workers: number
  failure_count: number
  retry_count: number
  provider_availability: Record<string, number>
  memory_usage_mb: number
  cpu_usage_percent: number
  disk_usage_percent: number
  timestamp: string
}

export interface AuditEntryDTO {
  id: string
  user_id: string
  action: string
  resource_type: string
  resource_id: string
  created_at: string
}

// --- Settings ---
export interface BrandKitDTO {
  logo_url: string
  primary_color: string
  secondary_color: string
  font_family: string
  intro_video_url: string
  outro_video_url: string
  watermark_url: string
}

export interface AIProviderConfigDTO {
  provider: string
  api_key_configured: boolean
  model: string
  enabled: boolean
  priority: number
}

export interface VoiceConfigDTO {
  provider: string
  voice_id: string
  language: string
  speed: number
  pitch: number
}

export interface StorageInfoDTO {
  used_bytes: number
  quota_bytes: number
  usage_percentage: number
}
