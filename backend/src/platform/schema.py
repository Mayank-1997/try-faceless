"""Platform Services Layer — all Pydantic v2 schemas and enums.

Defines data structures for:
- Analytics (project metrics, user activity, provider stats)
- Usage tracking (resource consumption)
- Billing (plans, credits, invoices, subscriptions)
- Cost analytics (per-project, per-user, per-provider breakdowns)
- Organizations (teams, members, roles, invitations)
- Notifications (email, in-app, webhook)
- Feature flags (toggles, beta features, A/B testing)
- Audit (platform-level audit events)
- Monitoring (system health, latency, queue metrics)
- Health (component health checks)
- Metrics (business, technical, financial, operational)
- API management (keys, rate limits, quotas)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class PlanType(str, Enum):
    """Billing plan types."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class SubscriptionStatus(str, Enum):
    """Subscription lifecycle status."""

    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAUSED = "paused"


class InvoiceStatus(str, Enum):
    """Invoice lifecycle status."""

    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    VOID = "void"


class CreditType(str, Enum):
    """Types of platform credits."""

    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    RENDER = "render"
    PUBLISH = "publish"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    UNIVERSAL = "universal"


class OrgRole(str, Enum):
    """Roles within an organization."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


class InvitationStatus(str, Enum):
    """Organization invitation status."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    REVOKED = "revoked"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""

    EMAIL = "email"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    TEAMS = "teams"


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    DISMISSED = "dismissed"


class FeatureFlagScope(str, Enum):
    """Feature flag scope levels."""

    GLOBAL = "global"
    USER = "user"
    ORGANIZATION = "organization"
    PLAN = "plan"


class FeatureFlagType(str, Enum):
    """Feature flag types."""

    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"
    VARIANT = "variant"


class PlatformAuditAction(str, Enum):
    """Platform-level audit actions."""

    PUBLISHING = "publishing"
    GENERATION = "generation"
    DELETION = "deletion"
    BILLING = "billing"
    ADMIN_CHANGE = "admin_change"
    ROLE_CHANGE = "role_change"
    SETTINGS_CHANGE = "settings_change"
    ORG_CHANGE = "org_change"
    FEATURE_FLAG_CHANGE = "feature_flag_change"
    API_KEY_CHANGE = "api_key_change"


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class MetricCategory(str, Enum):
    """Categories of metrics."""

    BUSINESS = "business"
    TECHNICAL = "technical"
    PERFORMANCE = "performance"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"


class MetricType(str, Enum):
    """Types of metric values."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class UsageResourceType(str, Enum):
    """Types of tracked resources."""

    IMAGES = "images"
    VIDEOS = "videos"
    VOICE_MINUTES = "voice_minutes"
    RENDERING_MINUTES = "rendering_minutes"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    PROJECTS = "projects"
    PUBLISHING = "publishing"
    TOKENS = "tokens"
    PROVIDER_CALLS = "provider_calls"


class ApiKeyScope(str, Enum):
    """API key permission scopes."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    FULL = "full"


# ---------------------------------------------------------------------------
# Analytics Models
# ---------------------------------------------------------------------------
class ProjectAnalytics(BaseModel):
    """Analytics for a single project."""

    project_id: str = ""
    user_id: str = ""
    generation_time_seconds: float = 0.0
    publishing_time_seconds: float = 0.0
    rendering_time_seconds: float = 0.0
    success: bool = True
    failure_reason: str = ""
    provider: str = ""
    model: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnalyticsSummary(BaseModel):
    """Aggregated analytics summary."""

    total_projects: int = 0
    successful_projects: int = 0
    failed_projects: int = 0
    avg_generation_time: float = 0.0
    avg_publishing_time: float = 0.0
    avg_rendering_time: float = 0.0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    most_used_providers: dict[str, int] = Field(default_factory=dict)
    top_models: dict[str, int] = Field(default_factory=dict)
    project_growth: list[dict[str, Any]] = Field(default_factory=list)
    user_activity: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Usage Tracking Models
# ---------------------------------------------------------------------------
class UsageRecord(BaseModel):
    """A single usage tracking record."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str = ""
    org_id: str = ""
    project_id: str = ""
    resource_type: UsageResourceType = UsageResourceType.PROJECTS
    amount: float = 0.0
    unit: str = ""
    provider: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UsageSummary(BaseModel):
    """Aggregated usage for a user or organization."""

    user_id: str = ""
    org_id: str = ""
    images_generated: int = 0
    videos_generated: int = 0
    voice_minutes: float = 0.0
    rendering_minutes: float = 0.0
    storage_bytes: int = 0
    bandwidth_bytes: int = 0
    projects_created: int = 0
    publishing_count: int = 0
    token_usage: int = 0
    provider_usage: dict[str, int] = Field(default_factory=dict)
    period_start: datetime | None = None
    period_end: datetime | None = None


# ---------------------------------------------------------------------------
# Billing Models
# ---------------------------------------------------------------------------
class PlanFeatures(BaseModel):
    """Features included in a billing plan."""

    max_projects: int = 5
    max_images_per_month: int = 100
    max_videos_per_month: int = 10
    max_voice_minutes_per_month: int = 30
    max_rendering_minutes_per_month: int = 60
    max_storage_gb: int = 5
    max_bandwidth_gb: int = 50
    max_team_members: int = 3
    custom_branding: bool = False
    priority_support: bool = False
    api_access: bool = False
    advanced_analytics: bool = False
    white_label: bool = False
    sso: bool = False


class Plan(BaseModel):
    """A billing plan."""

    id: str = ""
    name: str = ""
    plan_type: PlanType = PlanType.FREE
    price_monthly: float = 0.0
    price_yearly: float = 0.0
    currency: str = "USD"
    features: PlanFeatures = Field(default_factory=PlanFeatures)
    is_active: bool = True
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class Subscription(BaseModel):
    """A user's subscription."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str = ""
    org_id: str = ""
    plan_id: str = ""
    plan_type: PlanType = PlanType.FREE
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_period_start: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None
    trial_end: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)

    @property
    def is_trialing(self) -> bool:
        """Check if subscription is in trial."""
        return self.status == SubscriptionStatus.TRIALING


class CreditBalance(BaseModel):
    """Credit balance for a user or organization."""

    user_id: str = ""
    org_id: str = ""
    credits: dict[str, float] = Field(default_factory=dict)  # CreditType -> amount

    def get_balance(self, credit_type: str) -> float:
        """Get balance for a specific credit type."""
        return self.credits.get(credit_type, 0.0)

    def add_credits(self, credit_type: str, amount: float) -> float:
        """Add credits and return new balance."""
        current = self.credits.get(credit_type, 0.0)
        new_balance = current + amount
        self.credits[credit_type] = new_balance
        return new_balance

    def consume_credits(self, credit_type: str, amount: float) -> bool:
        """Consume credits if sufficient balance exists."""
        current = self.credits.get(credit_type, 0.0)
        if current < amount:
            return False
        self.credits[credit_type] = current - amount
        return True


class InvoiceItem(BaseModel):
    """A line item on an invoice."""

    description: str = ""
    quantity: float = 0.0
    unit_price: float = 0.0
    total: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Invoice(BaseModel):
    """A billing invoice."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str = ""
    org_id: str = ""
    subscription_id: UUID | None = None
    status: InvoiceStatus = InvoiceStatus.DRAFT
    items: list[InvoiceItem] = Field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    due_at: datetime | None = None
    paid_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def calculate_totals(self) -> None:
        """Recalculate subtotal and total from line items."""
        self.subtotal = sum(item.total for item in self.items)
        self.total = self.subtotal + self.tax


# ---------------------------------------------------------------------------
# Cost Analytics Models
# ---------------------------------------------------------------------------
class CostBreakdown(BaseModel):
    """Cost breakdown by dimension."""

    cost_per_project: dict[str, float] = Field(default_factory=dict)
    cost_per_user: dict[str, float] = Field(default_factory=dict)
    cost_per_provider: dict[str, float] = Field(default_factory=dict)
    cost_per_asset: dict[str, float] = Field(default_factory=dict)
    cost_per_workflow: dict[str, float] = Field(default_factory=dict)
    daily_costs: dict[str, float] = Field(default_factory=dict)  # date_str -> cost
    monthly_costs: dict[str, float] = Field(default_factory=dict)  # month_str -> cost
    total_cost: float = 0.0
    revenue: float = 0.0
    profit_margin: float = 0.0


# ---------------------------------------------------------------------------
# Organization Models
# ---------------------------------------------------------------------------
class Organization(BaseModel):
    """An organization."""

    id: UUID = Field(default_factory=uuid4)
    name: str = ""
    slug: str = ""
    owner_id: str = ""
    plan_type: PlanType = PlanType.FREE
    member_count: int = 0
    max_members: int = 10
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class TeamMember(BaseModel):
    """A member of an organization."""

    id: UUID = Field(default_factory=uuid4)
    org_id: UUID = Field(default_factory=uuid4)
    user_id: str = ""
    role: OrgRole = OrgRole.MEMBER
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    invited_by: str = ""
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class Invitation(BaseModel):
    """An organization invitation."""

    id: UUID = Field(default_factory=uuid4)
    org_id: UUID = Field(default_factory=uuid4)
    email: str = ""
    role: OrgRole = OrgRole.MEMBER
    status: InvitationStatus = InvitationStatus.PENDING
    invited_by: str = ""
    token: str = ""
    expires_at: datetime | None = None
    accepted_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_expired(self) -> bool:
        """Check if the invitation has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_pending(self) -> bool:
        """Check if the invitation is still pending."""
        return self.status == InvitationStatus.PENDING and not self.is_expired


class ProjectShare(BaseModel):
    """A project shared with a team member."""

    id: UUID = Field(default_factory=uuid4)
    project_id: str = ""
    shared_by: str = ""
    shared_with: str = ""
    role: OrgRole = OrgRole.VIEWER
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class Comment(BaseModel):
    """A comment on a project or scene."""

    id: UUID = Field(default_factory=uuid4)
    project_id: str = ""
    scene_id: str = ""
    user_id: str = ""
    content: str = ""
    resolved: bool = False
    parent_id: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class Approval(BaseModel):
    """An approval request for a project or scene."""

    id: UUID = Field(default_factory=uuid4)
    project_id: str = ""
    scene_id: str = ""
    requested_by: str = ""
    requested_to: str = ""
    status: str = "pending"  # pending, approved, rejected
    comment: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None


class ActivityFeedItem(BaseModel):
    """An item in the activity feed."""

    id: UUID = Field(default_factory=uuid4)
    org_id: str = ""
    user_id: str = ""
    action: str = ""
    resource_type: str = ""
    resource_id: str = ""
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Notification Models
# ---------------------------------------------------------------------------
class Notification(BaseModel):
    """A notification to be delivered."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str = ""
    org_id: str = ""
    channel: NotificationChannel = NotificationChannel.IN_APP
    priority: NotificationPriority = NotificationPriority.NORMAL
    status: NotificationStatus = NotificationStatus.PENDING
    title: str = ""
    body: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: datetime | None = None
    read_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebhookConfig(BaseModel):
    """Webhook configuration for notifications."""

    id: UUID = Field(default_factory=uuid4)
    org_id: str = ""
    url: str = ""
    events: list[str] = Field(default_factory=list)
    secret: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Feature Flag Models
# ---------------------------------------------------------------------------
class FeatureFlag(BaseModel):
    """A feature flag."""

    key: str = ""
    name: str = ""
    description: str = ""
    flag_type: FeatureFlagType = FeatureFlagType.BOOLEAN
    scope: FeatureFlagScope = FeatureFlagScope.GLOBAL
    enabled: bool = False
    percentage: float = 100.0  # For percentage rollouts
    variants: dict[str, Any] = Field(default_factory=dict)
    user_ids: list[str] = Field(default_factory=list)  # For user-level flags
    org_ids: list[str] = Field(default_factory=list)  # For org-level flags
    plan_types: list[str] = Field(default_factory=list)  # For plan-level flags
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Audit Models
# ---------------------------------------------------------------------------
class PlatformAuditEntry(BaseModel):
    """A platform-level audit entry."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str = ""
    org_id: str = ""
    action: PlatformAuditAction = PlatformAuditAction.ADMIN_CHANGE
    resource_type: str = ""
    resource_id: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    correlation_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Monitoring & Health Models
# ---------------------------------------------------------------------------
class HealthCheck(BaseModel):
    """Result of a health check for a component."""

    component: str = ""
    status: HealthStatus = HealthStatus.UNKNOWN
    latency_ms: float = 0.0
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthReport(BaseModel):
    """Overall health report for the platform."""

    overall_status: HealthStatus = HealthStatus.UNKNOWN
    checks: list[HealthCheck] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def healthy_count(self) -> int:
        """Number of healthy components."""
        return sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY)

    @property
    def unhealthy_count(self) -> int:
        """Number of unhealthy components."""
        return sum(1 for c in self.checks if c.status == HealthStatus.UNHEALTHY)

    @property
    def degraded_count(self) -> int:
        """Number of degraded components."""
        return sum(1 for c in self.checks if c.status == HealthStatus.DEGRADED)


class MonitoringMetric(BaseModel):
    """A monitoring metric sample."""

    name: str = ""
    value: float = 0.0
    unit: str = ""
    labels: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MonitoringSnapshot(BaseModel):
    """A snapshot of monitoring metrics."""

    latency_ms: float = 0.0
    queue_size: int = 0
    worker_count: int = 0
    active_workers: int = 0
    failure_count: int = 0
    retry_count: int = 0
    provider_availability: dict[str, float] = Field(default_factory=dict)
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    disk_usage_percent: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Metrics Models
# ---------------------------------------------------------------------------
class Metric(BaseModel):
    """A collected metric."""

    name: str = ""
    category: MetricCategory = MetricCategory.BUSINESS
    metric_type: MetricType = MetricType.COUNTER
    value: float = 0.0
    unit: str = ""
    labels: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricSummary(BaseModel):
    """Summary of metrics by category."""

    business: dict[str, float] = Field(default_factory=dict)
    technical: dict[str, float] = Field(default_factory=dict)
    performance: dict[str, float] = Field(default_factory=dict)
    financial: dict[str, float] = Field(default_factory=dict)
    operational: dict[str, float] = Field(default_factory=dict)
    period_start: datetime | None = None
    period_end: datetime | None = None


# ---------------------------------------------------------------------------
# API Management Models
# ---------------------------------------------------------------------------
class ApiKeyInfo(BaseModel):
    """API key information (without the actual key)."""

    id: UUID = Field(default_factory=uuid4)
    user_id: str = ""
    org_id: str = ""
    name: str = ""
    scopes: list[ApiKeyScope] = Field(default_factory=list)
    rate_limit_per_minute: int = 60
    rate_limit_per_day: int = 10000
    is_active: bool = True
    last_used_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= self.expires_at


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""

    requests_per_minute: int = 60
    requests_per_hour: int = 3600
    requests_per_day: int = 10000
    burst_limit: int = 10
    metadata: dict[str, Any] = Field(default_factory=dict)


class Quota(BaseModel):
    """A usage quota for a resource."""

    user_id: str = ""
    org_id: str = ""
    resource_type: UsageResourceType = UsageResourceType.PROJECTS
    limit: float = 0.0
    used: float = 0.0
    period: str = "monthly"
    reset_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def remaining(self) -> float:
        """Remaining quota."""
        return max(0.0, self.limit - self.used)

    @property
    def is_exhausted(self) -> bool:
        """Check if quota is exhausted."""
        return self.used >= self.limit > 0

    @property
    def usage_percentage(self) -> float:
        """Usage as a percentage of limit."""
        if self.limit <= 0:
            return 0.0
        return (self.used / self.limit) * 100.0
