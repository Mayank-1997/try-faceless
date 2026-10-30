// =============================================================================
// Shared Types — Enums matching backend src/core/enums.py
// =============================================================================

export enum UserStatus {
  PENDING = 'pending',
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  DELETED = 'deleted',
  LOCKED = 'locked',
}

export enum AuthProvider {
  LOCAL = 'local',
  GOOGLE = 'google',
  GITHUB = 'github',
  MICROSOFT = 'microsoft',
  APPLE = 'apple',
  LINKEDIN = 'linkedin',
}

export enum ApiKeyStatus {
  ACTIVE = 'active',
  REVOKED = 'revoked',
  EXPIRED = 'expired',
}

export enum SessionStatus {
  ACTIVE = 'active',
  REVOKED = 'revoked',
  EXPIRED = 'expired',
}

export enum TokenType {
  ACCESS = 'access',
  REFRESH = 'refresh',
}

export enum AuditAction {
  LOGIN = 'login',
  LOGOUT = 'logout',
  LOGIN_FAILED = 'login_failed',
  REGISTER = 'register',
  PASSWORD_CHANGE = 'password_change',
  PASSWORD_RESET = 'password_reset',
  EMAIL_VERIFIED = 'email_verified',
  API_KEY_CREATED = 'api_key_created',
  API_KEY_REVOKED = 'api_key_revoked',
  SESSION_REVOKED = 'session_revoked',
  ROLE_ASSIGNED = 'role_assigned',
  ROLE_REMOVED = 'role_removed',
  USER_SUSPENDED = 'user_suspended',
  USER_ACTIVATED = 'user_activated',
  PROFILE_UPDATED = 'profile_updated',
}

export enum ThemePreference {
  LIGHT = 'light',
  DARK = 'dark',
  SYSTEM = 'system',
}

export enum DefaultRoleName {
  SUPER_ADMIN = 'super_admin',
  ADMIN = 'admin',
  CREATOR = 'creator',
  VIEWER = 'viewer',
}

export enum ContentType {
  YOUTUBE_VIDEO = 'youtube_video',
  BLOG = 'blog',
  LINKEDIN = 'linkedin',
  TWITTER = 'twitter',
  INSTAGRAM = 'instagram',
  PODCAST = 'podcast',
  DOCUMENTATION = 'documentation',
  COURSE = 'course',
}

export enum VideoStyle {
  CINEMATIC = 'cinematic',
  DOCUMENTARY = 'documentary',
  EXPLAINER = 'explainer',
  TALKING_HEAD = 'talking_head',
  ANIMATED = 'animated',
  MIXED = 'mixed',
  STOCK_FOOTAGE = 'stock_footage',
  WHITEBOARD = 'whiteboard',
}

export enum WorkflowStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum WorkflowStep {
  INITIALIZATION = 'initialization',
  RESEARCH = 'research',
  SCRIPTING = 'scripting',
  STORYBOARD = 'storyboard',
  SCENE_PLANNING = 'scene_planning',
  ASSET_GENERATION = 'asset_generation',
  VOICE_GENERATION = 'voice_generation',
  SUBTITLE_GENERATION = 'subtitle_generation',
  RENDERING = 'rendering',
  THUMBNAIL = 'thumbnail',
  SEO = 'seo',
  // PUBLISHING is temporarily disabled; SEO is the final step
  // PUBLISHING = 'publishing',
  COMPLETED = 'completed',
}

export enum ResearchStatus {
  DRAFT = 'draft',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  SUPERSEDED = 'superseded',
}

export enum ScriptStatus {
  DRAFT = 'draft',
  IN_REVIEW = 'in_review',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  SUPERSEDED = 'superseded',
}

export enum StoryboardStatus {
  DRAFT = 'draft',
  IN_REVIEW = 'in_review',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  SUPERSEDED = 'superseded',
}

export enum SceneGenerationStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  GENERATED = 'generated',
  PARTIALLY_GENERATED = 'partially_generated',
  FAILED = 'failed',
  SKIPPED = 'skipped',
}

export enum SceneReviewStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  NEEDS_REVISION = 'needs_revision',
}

export enum AssetGenerationStatus {
  PLANNED = 'planned',
  QUEUED = 'queued',
  GENERATING = 'generating',
  READY = 'ready',
  FAILED = 'failed',
  REJECTED = 'rejected',
  REGENERATED = 'regenerated',
}

export enum JobType {
  RESEARCH = 'research',
  SCRIPT = 'script',
  SCENE = 'scene',
  IMAGE = 'image',
  VIDEO = 'video',
  VOICE = 'voice',
  SUBTITLE = 'subtitle',
  RENDERING = 'rendering',
  THUMBNAIL = 'thumbnail',
  SEO = 'seo',
  PUBLISHING = 'publishing',
}

export enum CostPeriod {
  DAILY = 'daily',
  WEEKLY = 'weekly',
  MONTHLY = 'monthly',
  YEARLY = 'yearly',
}

export enum AIProvider {
  GEMINI = 'gemini',
  OPENAI = 'openai',
  CLAUDE = 'claude',
  IMAGEN = 'imagen',
  VEO = 'veo',
  RUNWAY = 'runway',
  FAL = 'fal',
  GOOGLE_TTS = 'google_tts',
  ELEVENLABS = 'elevenlabs',
}

export enum AgentType {
  DIRECTOR = 'director',
  RESEARCHER = 'researcher',
  SCRIPTWRITER = 'scriptwriter',
  STORYBOARDER = 'storyboarder',
  SCENE_PLANNER = 'scene_planner',
  ASSET_GENERATOR = 'asset_generator',
  VOICE_DIRECTOR = 'voice_director',
  SUBTITLE_EDITOR = 'subtitle_editor',
  SEO_SPECIALIST = 'seo_specialist',
  THUMBNAIL_DESIGNER = 'thumbnail_designer',
  QUALITY_REVIEWER = 'quality_reviewer',
}

// =============================================================================
// Platform Service Enums (Phase 12)
// =============================================================================

export enum PlanType {
  FREE = 'free',
  PRO = 'pro',
  ENTERPRISE = 'enterprise',
  CUSTOM = 'custom',
}

export enum SubscriptionStatus {
  ACTIVE = 'active',
  TRIALING = 'trialing',
  PAST_DUE = 'past_due',
  CANCELLED = 'cancelled',
  EXPIRED = 'expired',
  PAUSED = 'paused',
}

export enum InvoiceStatus {
  DRAFT = 'draft',
  PENDING = 'pending',
  PAID = 'paid',
  FAILED = 'failed',
  REFUNDED = 'refunded',
  VOID = 'void',
}

export enum CreditType {
  IMAGE = 'image',
  VIDEO = 'video',
  VOICE = 'voice',
  RENDER = 'render',
  PUBLISH = 'publish',
  STORAGE = 'storage',
  BANDWIDTH = 'bandwidth',
  UNIVERSAL = 'universal',
}

export enum OrgRole {
  OWNER = 'owner',
  ADMIN = 'admin',
  MEMBER = 'member',
  VIEWER = 'viewer',
  GUEST = 'guest',
}

export enum InvitationStatus {
  PENDING = 'pending',
  ACCEPTED = 'accepted',
  DECLINED = 'declined',
  EXPIRED = 'expired',
  REVOKED = 'revoked',
}

export enum NotificationChannel {
  EMAIL = 'email',
  IN_APP = 'in_app',
  WEBHOOK = 'webhook',
  SLACK = 'slack',
  DISCORD = 'discord',
  TEAMS = 'teams',
}

export enum NotificationPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent',
}

export enum NotificationStatus {
  PENDING = 'pending',
  SENT = 'sent',
  DELIVERED = 'delivered',
  READ = 'read',
  FAILED = 'failed',
  DISMISSED = 'dismissed',
}

export enum FeatureFlagScope {
  GLOBAL = 'global',
  USER = 'user',
  ORGANIZATION = 'organization',
  PLAN = 'plan',
}

export enum FeatureFlagType {
  BOOLEAN = 'boolean',
  PERCENTAGE = 'percentage',
  VARIANT = 'variant',
}

export enum HealthStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  UNHEALTHY = 'unhealthy',
  UNKNOWN = 'unknown',
}

export enum MetricCategory {
  BUSINESS = 'business',
  TECHNICAL = 'technical',
  PERFORMANCE = 'performance',
  FINANCIAL = 'financial',
  OPERATIONAL = 'operational',
}

export enum UsageResourceType {
  IMAGES = 'images',
  VIDEOS = 'videos',
  VOICE_MINUTES = 'voice_minutes',
  RENDERING_MINUTES = 'rendering_minutes',
  STORAGE = 'storage',
  BANDWIDTH = 'bandwidth',
  PROJECTS = 'projects',
  PUBLISHING = 'publishing',
  TOKENS = 'tokens',
  PROVIDER_CALLS = 'provider_calls',
}

// =============================================================================
// Publishing Enums (Phase 11)
// =============================================================================

export enum PublishingPlatform {
  YOUTUBE = 'youtube',
  LINKEDIN = 'linkedin',
  MEDIUM = 'medium',
  WORDPRESS = 'wordpress',
  TWITTER = 'twitter',
  FACEBOOK = 'facebook',
  INSTAGRAM = 'instagram',
  TIKTOK = 'tiktok',
  PODCAST = 'podcast',
}

export enum PublishingMode {
  IMMEDIATE = 'immediate',
  SCHEDULED = 'scheduled',
  DRAFT = 'draft',
}

export enum PublishingJobStatus {
  QUEUED = 'queued',
  UPLOADING = 'uploading',
  THUMBNAIL_UPLOAD = 'thumbnail_upload',
  METADATA_UPDATE = 'metadata_update',
  PUBLISHING = 'publishing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum PublishingPriority {
  CRITICAL = 'critical',
  HIGH = 'high',
  NORMAL = 'normal',
  LOW = 'low',
  BACKGROUND = 'background',
}

export enum AuthMethod {
  OAUTH2 = 'oauth2',
  API_KEY = 'api_key',
}

export enum RetryStrategy {
  EXPONENTIAL_BACKOFF = 'exponential_backoff',
  LINEAR_BACKOFF = 'linear_backoff',
  FIXED_DELAY = 'fixed_delay',
  NONE = 'none',
}

export enum FailoverStrategy {
  SKIP_FAILED = 'skip_failed',
  RETRY_ALTERNATIVE = 'retry_alternative',
  ABORT_ALL = 'abort_all',
}
