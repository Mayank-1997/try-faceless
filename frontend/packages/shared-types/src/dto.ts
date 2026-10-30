// =============================================================================
// API DTOs — matching backend src/application/dto/auth_dtos.py
// =============================================================================

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserResponse
}

export interface UserResponse {
  id: string
  email: string
  username: string
  first_name: string
  last_name: string
  full_name: string
  profile_image_url: string | null
  phone: string | null
  status: string
  auth_provider: string
  timezone: string
  language: string
  email_verified: boolean
  two_factor_enabled: boolean
  roles: string[]
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface UserListResponse {
  users: UserResponse[]
  total: number
  offset: number
  limit: number
}

export interface UserPreferencesResponse {
  theme: string
  language: string
  default_ai_model: string
  preferred_llm: string
  preferred_voice: string
  preferred_image_provider: string
  preferred_video_provider: string
  email_notifications: boolean
  push_notifications: boolean
}

export interface ApiKeyResponse {
  id: string
  name: string
  key_prefix: string
  status: string
  scopes: string[]
  expires_at: string | null
  last_used_at: string | null
  created_at: string
}

export interface ApiKeyWithSecretResponse extends ApiKeyResponse {
  key: string
}

export interface SessionResponse {
  id: string
  device: string
  browser: string
  operating_system: string
  ip_address: string
  status: string
  created_at: string
  last_activity_at: string
  expires_at: string | null
  is_current: boolean
}

export interface SessionListResponse {
  sessions: SessionResponse[]
  total: number
}

export interface RoleResponse {
  id: string
  name: string
  description: string
  is_system: boolean
  permissions: string[]
  created_at: string
}

export interface PermissionResponse {
  id: string
  name: string
  description: string
  resource: string
  action: string
  is_system: boolean
}

export interface AuditLogResponse {
  id: string
  user_id: string | null
  action: string
  resource_type: string
  resource_id: string | null
  ip_address: string
  details: Record<string, unknown>
  correlation_id: string | null
  created_at: string
}

export interface MessageResponse {
  message: string
}

// =============================================================================
// Request DTOs
// =============================================================================

export interface RegisterRequest {
  email: string
  username: string
  password: string
  first_name?: string
  last_name?: string
}

export interface LoginRequest {
  email: string
  password: string
  remember_me?: boolean
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface ForgotPasswordRequest {
  email: string
}

export interface ResetPasswordRequest {
  token: string
  new_password: string
}

export interface VerifyEmailRequest {
  token: string
}

export interface ResendVerificationRequest {
  email: string
}

export interface UpdateProfileRequest {
  first_name?: string
  last_name?: string
  profile_image_url?: string
  phone?: string
  timezone?: string
  language?: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

export interface UpdatePreferencesRequest {
  theme?: string
  language?: string
  default_ai_model?: string
  preferred_llm?: string
  preferred_voice?: string
  preferred_image_provider?: string
  preferred_video_provider?: string
  email_notifications?: boolean
  push_notifications?: boolean
}

export interface CreateApiKeyRequest {
  name: string
  scopes?: string[]
  expires_in_days?: number
}

export interface UpdateApiKeyRequest {
  name?: string
  scopes?: string[]
}

export interface CreateRoleRequest {
  name: string
  description?: string
  permission_ids?: string[]
}

// =============================================================================
// Platform Service Types (Phase 12)
// =============================================================================

export interface ProjectAnalytics {
  project_id: string
  user_id: string
  generation_time_seconds: number
  publishing_time_seconds: number
  rendering_time_seconds: number
  success: boolean
  failure_reason: string
  provider: string
  model: string
  created_at: string
}

export interface AnalyticsSummary {
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

export interface UsageSummary {
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
  period_start: string | null
  period_end: string | null
}

export interface Plan {
  id: string
  name: string
  plan_type: string
  price_monthly: number
  price_yearly: number
  currency: string
  features: PlanFeatures
  is_active: boolean
  description: string
}

export interface PlanFeatures {
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

export interface Subscription {
  id: string
  user_id: string
  org_id: string
  plan_id: string
  plan_type: string
  status: string
  started_at: string
  current_period_start: string
  current_period_end: string | null
  cancelled_at: string | null
  trial_end: string | null
}

export interface CreditBalance {
  user_id: string
  org_id: string
  credits: Record<string, number>
}

export interface Invoice {
  id: string
  user_id: string
  org_id: string
  subscription_id: string | null
  status: string
  items: InvoiceItem[]
  subtotal: number
  tax: number
  total: number
  currency: string
  issued_at: string
  due_at: string | null
  paid_at: string | null
}

export interface InvoiceItem {
  description: string
  quantity: number
  unit_price: number
  total: number
}

export interface Organization {
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

export interface TeamMember {
  id: string
  org_id: string
  user_id: string
  role: string
  joined_at: string
  invited_by: string
  is_active: boolean
}

export interface Invitation {
  id: string
  org_id: string
  email: string
  role: string
  status: string
  invited_by: string
  token: string
  expires_at: string | null
  accepted_at: string | null
  created_at: string
}

export interface Notification {
  id: string
  user_id: string
  org_id: string
  channel: string
  priority: string
  status: string
  title: string
  body: string
  data: Record<string, unknown>
  created_at: string
  sent_at: string | null
  read_at: string | null
}

export interface HealthCheck {
  component: string
  status: string
  latency_ms: number
  message: string
  details: Record<string, unknown>
  checked_at: string
}

export interface HealthReport {
  overall_status: string
  checks: HealthCheck[]
  checked_at: string
}

export interface MonitoringSnapshot {
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

export interface Quota {
  user_id: string
  org_id: string
  resource_type: string
  limit: number
  used: number
  period: string
  reset_at: string | null
}

export interface ApiKeyInfo {
  id: string
  user_id: string
  org_id: string
  name: string
  scopes: string[]
  rate_limit_per_minute: number
  rate_limit_per_day: number
  is_active: boolean
  last_used_at: string | null
  created_at: string
  expires_at: string | null
}

// =============================================================================
// Generic API Types
// =============================================================================

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  offset: number
  limit: number
}

export interface ApiError {
  error: string
  message: string
  details?: Record<string, unknown>
  status_code: number
  correlation_id?: string
}

export type ApiResponse<T> = T | ApiError
