"""Platform Services Layer — Phase 12.

Provides reusable infrastructure for analytics, billing, monitoring,
collaboration, notifications, and administration.

This layer remains independent from content generation logic.

Services:
    AnalyticsService — Project analytics and aggregated summaries
    UsageTracker — Resource usage tracking
    BillingService — Plans, credits, subscriptions, invoices
    CostAnalyticsService — Cost breakdowns across dimensions
    OrganizationService — Orgs, teams, members, invitations, collaboration
    NotificationService — Multi-channel notifications and webhooks
    FeatureFlagService — Feature toggles, beta features, A/B testing
    PlatformAuditService — Platform-level audit logging
    MonitoringService — System monitoring metrics
    HealthService — Component health checks
    MetricsService — Business, technical, financial metrics
    ApiManagementService — API keys, rate limits, quotas
    AdminService — Administrative dashboard and management
"""

from __future__ import annotations

# Schema
from src.platform.schema import (
    ActivityFeedItem,
    AnalyticsSummary,
    ApiKeyInfo,
    ApiKeyScope,
    Approval,
    Comment,
    CostBreakdown,
    CreditBalance,
    CreditType,
    FeatureFlag,
    FeatureFlagScope,
    FeatureFlagType,
    HealthCheck,
    HealthReport,
    HealthStatus,
    Invitation,
    InvitationStatus,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Metric,
    MetricCategory,
    MetricSummary,
    MetricType,
    MonitoringMetric,
    MonitoringSnapshot,
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    OrgRole,
    Organization,
    Plan,
    PlanFeatures,
    PlanType,
    PlatformAuditAction,
    PlatformAuditEntry,
    ProjectAnalytics,
    ProjectShare,
    Quota,
    RateLimitConfig,
    Subscription,
    SubscriptionStatus,
    TeamMember,
    UsageRecord,
    UsageResourceType,
    UsageSummary,
    WebhookConfig,
)

# Services
from src.platform.analytics import AnalyticsService
from src.platform.usage import UsageTracker
from src.platform.billing import BillingService
from src.platform.cost_analytics import CostAnalyticsService
from src.platform.organization import OrganizationService
from src.platform.notification import NotificationService
from src.platform.feature_flags import FeatureFlagService
from src.platform.audit import PlatformAuditService
from src.platform.monitoring import HealthService, MonitoringService
from src.platform.metrics import MetricsService
from src.platform.api_management import ApiManagementService
from src.platform.admin import AdminService

__all__ = [
    # Schema
    "ActivityFeedItem",
    "AnalyticsSummary",
    "ApiKeyInfo",
    "ApiKeyScope",
    "Approval",
    "Comment",
    "CostBreakdown",
    "CreditBalance",
    "CreditType",
    "FeatureFlag",
    "FeatureFlagScope",
    "FeatureFlagType",
    "HealthCheck",
    "HealthReport",
    "HealthStatus",
    "Invitation",
    "InvitationStatus",
    "Invoice",
    "InvoiceItem",
    "InvoiceStatus",
    "Metric",
    "MetricCategory",
    "MetricSummary",
    "MetricType",
    "MonitoringMetric",
    "MonitoringSnapshot",
    "Notification",
    "NotificationChannel",
    "NotificationPriority",
    "NotificationStatus",
    "OrgRole",
    "Organization",
    "Plan",
    "PlanFeatures",
    "PlanType",
    "PlatformAuditAction",
    "PlatformAuditEntry",
    "ProjectAnalytics",
    "ProjectShare",
    "Quota",
    "RateLimitConfig",
    "Subscription",
    "SubscriptionStatus",
    "TeamMember",
    "UsageRecord",
    "UsageResourceType",
    "UsageSummary",
    "WebhookConfig",
    # Services
    "AnalyticsService",
    "UsageTracker",
    "BillingService",
    "CostAnalyticsService",
    "OrganizationService",
    "NotificationService",
    "FeatureFlagService",
    "PlatformAuditService",
    "MonitoringService",
    "HealthService",
    "MetricsService",
    "ApiManagementService",
    "AdminService",
]
