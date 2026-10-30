"""Comprehensive tests for the Platform Services Layer (Phase 12).

Covers:
- Schema tests (all models, enums, defaults, computed properties)
- Analytics Service tests
- Usage Tracker tests
- Billing Service tests
- Cost Analytics tests
- Organization Service tests
- Notification Service tests
- Feature Flag Service tests
- Platform Audit Service tests
- Monitoring Service tests
- Health Service tests
- Metrics Service tests
- API Management Service tests
- Admin Service tests
- Integration tests
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

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


# ===========================================================================
# Schema Tests
# ===========================================================================
class TestSchema:
    def test_plan_type_values(self):
        assert PlanType.FREE == "free"
        assert PlanType.PRO == "pro"
        assert PlanType.ENTERPRISE == "enterprise"

    def test_subscription_status_values(self):
        assert SubscriptionStatus.ACTIVE == "active"
        assert SubscriptionStatus.TRIALING == "trialing"
        assert SubscriptionStatus.CANCELLED == "cancelled"

    def test_invoice_status_values(self):
        assert InvoiceStatus.DRAFT == "draft"
        assert InvoiceStatus.PAID == "paid"
        assert InvoiceStatus.FAILED == "failed"

    def test_credit_type_values(self):
        assert CreditType.IMAGE == "image"
        assert CreditType.VIDEO == "video"
        assert CreditType.UNIVERSAL == "universal"

    def test_org_role_values(self):
        assert OrgRole.OWNER == "owner"
        assert OrgRole.ADMIN == "admin"
        assert OrgRole.MEMBER == "member"
        assert OrgRole.VIEWER == "viewer"

    def test_invitation_status_values(self):
        assert InvitationStatus.PENDING == "pending"
        assert InvitationStatus.ACCEPTED == "accepted"
        assert InvitationStatus.DECLINED == "declined"

    def test_notification_channel_values(self):
        assert NotificationChannel.EMAIL == "email"
        assert NotificationChannel.IN_APP == "in_app"
        assert NotificationChannel.WEBHOOK == "webhook"

    def test_notification_priority_values(self):
        assert NotificationPriority.LOW == "low"
        assert NotificationPriority.NORMAL == "normal"
        assert NotificationPriority.HIGH == "high"
        assert NotificationPriority.URGENT == "urgent"

    def test_feature_flag_scope_values(self):
        assert FeatureFlagScope.GLOBAL == "global"
        assert FeatureFlagScope.USER == "user"
        assert FeatureFlagScope.ORGANIZATION == "organization"

    def test_feature_flag_type_values(self):
        assert FeatureFlagType.BOOLEAN == "boolean"
        assert FeatureFlagType.PERCENTAGE == "percentage"
        assert FeatureFlagType.VARIANT == "variant"

    def test_health_status_values(self):
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"

    def test_metric_category_values(self):
        assert MetricCategory.BUSINESS == "business"
        assert MetricCategory.TECHNICAL == "technical"
        assert MetricCategory.FINANCIAL == "financial"

    def test_metric_type_values(self):
        assert MetricType.COUNTER == "counter"
        assert MetricType.GAUGE == "gauge"
        assert MetricType.HISTOGRAM == "histogram"

    def test_usage_resource_type_values(self):
        assert UsageResourceType.IMAGES == "images"
        assert UsageResourceType.VIDEOS == "videos"
        assert UsageResourceType.TOKENS == "tokens"

    def test_api_key_scope_values(self):
        assert ApiKeyScope.READ == "read"
        assert ApiKeyScope.WRITE == "write"
        assert ApiKeyScope.ADMIN == "admin"

    def test_plan_features_defaults(self):
        features = PlanFeatures()
        assert features.max_projects == 5
        assert features.custom_branding is False

    def test_subscription_is_active(self):
        sub = Subscription(status=SubscriptionStatus.ACTIVE)
        assert sub.is_active is True
        sub2 = Subscription(status=SubscriptionStatus.CANCELLED)
        assert sub2.is_active is False

    def test_subscription_is_trialing(self):
        sub = Subscription(status=SubscriptionStatus.TRIALING)
        assert sub.is_trialing is True

    def test_credit_balance_operations(self):
        balance = CreditBalance(user_id="user1")
        assert balance.get_balance("image") == 0.0
        balance.add_credits("image", 100)
        assert balance.get_balance("image") == 100.0
        assert balance.consume_credits("image", 30) is True
        assert balance.get_balance("image") == 70.0
        assert balance.consume_credits("image", 100) is False

    def test_invoice_calculate_totals(self):
        items = [
            InvoiceItem(description="Item 1", quantity=2, unit_price=10, total=20),
            InvoiceItem(description="Item 2", quantity=1, unit_price=50, total=50),
        ]
        invoice = Invoice(items=items, tax=5)
        invoice.calculate_totals()
        assert invoice.subtotal == 70
        assert invoice.total == 75

    def test_invitation_is_expired(self):
        inv = Invitation(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
        assert inv.is_expired is True
        inv2 = Invitation(expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
        assert inv2.is_expired is False

    def test_invitation_is_pending(self):
        inv = Invitation(
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert inv.is_pending is True

    def test_health_report_counts(self):
        report = HealthReport(checks=[
            HealthCheck(component="db", status=HealthStatus.HEALTHY),
            HealthCheck(component="redis", status=HealthStatus.UNHEALTHY),
            HealthCheck(component="storage", status=HealthStatus.DEGRADED),
        ])
        assert report.healthy_count == 1
        assert report.unhealthy_count == 1
        assert report.degraded_count == 1

    def test_api_key_info_is_expired(self):
        key = ApiKeyInfo(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
        assert key.is_expired is True
        key2 = ApiKeyInfo(expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
        assert key2.is_expired is False

    def test_quota_remaining(self):
        quota = Quota(limit=100, used=30)
        assert quota.remaining == 70
        assert quota.is_exhausted is False
        quota2 = Quota(limit=100, used=100)
        assert quota2.is_exhausted is True
        assert quota2.remaining == 0

    def test_quota_usage_percentage(self):
        quota = Quota(limit=100, used=50)
        assert quota.usage_percentage == 50.0

    def test_project_analytics_defaults(self):
        analytics = ProjectAnalytics()
        assert analytics.success is True
        assert analytics.generation_time_seconds == 0.0


# ===========================================================================
# Analytics Service Tests
# ===========================================================================
class TestAnalyticsService:
    def test_record_and_get_summary(self):
        svc = AnalyticsService()
        svc.record(ProjectAnalytics(
            project_id="p1",
            user_id="u1",
            generation_time_seconds=120,
            publishing_time_seconds=30,
            rendering_time_seconds=60,
            success=True,
            provider="gemini",
            model="gemini-2.0-flash",
        ))
        svc.record(ProjectAnalytics(
            project_id="p2",
            user_id="u1",
            generation_time_seconds=80,
            success=False,
            failure_reason="timeout",
            provider="veo",
            model="veo-3.0",
        ))
        summary = svc.get_summary()
        assert summary.total_projects == 2
        assert summary.successful_projects == 1
        assert summary.failed_projects == 1
        assert summary.success_rate == 50.0
        assert summary.failure_rate == 50.0
        assert "gemini" in summary.most_used_providers
        assert "veo" in summary.most_used_providers

    def test_get_summary_empty(self):
        svc = AnalyticsService()
        summary = svc.get_summary()
        assert summary.total_projects == 0

    def test_get_user_activity(self):
        svc = AnalyticsService()
        svc.record(ProjectAnalytics(project_id="p1", user_id="u1"))
        svc.record(ProjectAnalytics(project_id="p2", user_id="u2"))
        records = svc.get_user_activity("u1")
        assert len(records) == 1
        assert records[0].user_id == "u1"

    def test_get_project_analytics(self):
        svc = AnalyticsService()
        svc.record(ProjectAnalytics(project_id="p1", user_id="u1"))
        result = svc.get_project_analytics("p1")
        assert result is not None
        assert result.project_id == "p1"

    def test_get_project_analytics_not_found(self):
        svc = AnalyticsService()
        assert svc.get_project_analytics("nonexistent") is None

    def test_filter_by_user(self):
        svc = AnalyticsService()
        svc.record(ProjectAnalytics(project_id="p1", user_id="u1"))
        svc.record(ProjectAnalytics(project_id="p2", user_id="u2"))
        summary = svc.get_summary(user_id="u1")
        assert summary.total_projects == 1

    def test_record_count(self):
        svc = AnalyticsService()
        svc.record(ProjectAnalytics(project_id="p1"))
        assert svc.record_count == 1

    def test_clear(self):
        svc = AnalyticsService()
        svc.record(ProjectAnalytics())
        svc.clear()
        assert svc.record_count == 0


# ===========================================================================
# Usage Tracker Tests
# ===========================================================================
class TestUsageTracker:
    def test_record_image_generation(self):
        tracker = UsageTracker()
        tracker.record_image_generation("u1", count=5)
        summary = tracker.get_summary("u1")
        assert summary.images_generated == 5

    def test_record_video_generation(self):
        tracker = UsageTracker()
        tracker.record_video_generation("u1", count=3)
        summary = tracker.get_summary("u1")
        assert summary.videos_generated == 3

    def test_record_voice_minutes(self):
        tracker = UsageTracker()
        tracker.record_voice_minutes("u1", 15.5)
        summary = tracker.get_summary("u1")
        assert summary.voice_minutes == 15.5

    def test_record_rendering_minutes(self):
        tracker = UsageTracker()
        tracker.record_rendering_minutes("u1", 45.0)
        summary = tracker.get_summary("u1")
        assert summary.rendering_minutes == 45.0

    def test_record_storage(self):
        tracker = UsageTracker()
        tracker.record_storage("u1", 1024 * 1024 * 100)  # 100MB
        summary = tracker.get_summary("u1")
        assert summary.storage_bytes == 100 * 1024 * 1024

    def test_record_publishing(self):
        tracker = UsageTracker()
        tracker.record_publishing("u1", count=2)
        summary = tracker.get_summary("u1")
        assert summary.publishing_count == 2

    def test_record_tokens(self):
        tracker = UsageTracker()
        tracker.record_tokens("u1", 50000)
        summary = tracker.get_summary("u1")
        assert summary.token_usage == 50000

    def test_get_org_summary(self):
        tracker = UsageTracker()
        tracker.record(UsageRecord(user_id="u1", org_id="org1", resource_type=UsageResourceType.IMAGES, amount=10))
        tracker.record(UsageRecord(user_id="u2", org_id="org1", resource_type=UsageResourceType.IMAGES, amount=5))
        summary = tracker.get_org_summary("org1")
        assert summary.images_generated == 15

    def test_record_count(self):
        tracker = UsageTracker()
        tracker.record_image_generation("u1")
        assert tracker.record_count == 1

    def test_clear(self):
        tracker = UsageTracker()
        tracker.record_image_generation("u1")
        tracker.clear()
        assert tracker.record_count == 0


# ===========================================================================
# Billing Service Tests
# ===========================================================================
class TestBillingService:
    def test_get_plan(self):
        svc = BillingService()
        plan = svc.get_plan("free")
        assert plan is not None
        assert plan.plan_type == PlanType.FREE
        assert plan.price_monthly == 0.0

    def test_get_plan_not_found(self):
        svc = BillingService()
        assert svc.get_plan("nonexistent") is None

    def test_list_plans(self):
        svc = BillingService()
        plans = svc.list_plans()
        assert len(plans) == 3

    def test_create_plan(self):
        svc = BillingService()
        plan = Plan(id="custom", name="Custom", plan_type=PlanType.CUSTOM, price_monthly=50.0)
        svc.create_plan(plan)
        assert svc.get_plan("custom") is not None

    def test_create_subscription(self):
        svc = BillingService()
        sub = svc.create_subscription("u1", "pro")
        assert sub.user_id == "u1"
        assert sub.plan_id == "pro"
        assert sub.status == SubscriptionStatus.ACTIVE

    def test_create_subscription_trial(self):
        svc = BillingService()
        sub = svc.create_subscription("u1", "pro", trial_days=14)
        assert sub.is_trialing is True
        assert sub.trial_end is not None

    def test_create_subscription_invalid_plan(self):
        svc = BillingService()
        with pytest.raises(ValueError):
            svc.create_subscription("u1", "nonexistent")

    def test_get_subscription(self):
        svc = BillingService()
        svc.create_subscription("u1", "free")
        sub = svc.get_subscription("u1")
        assert sub is not None

    def test_cancel_subscription(self):
        svc = BillingService()
        svc.create_subscription("u1", "pro")
        cancelled = svc.cancel_subscription("u1")
        assert cancelled.status == SubscriptionStatus.CANCELLED

    def test_cancel_subscription_not_found(self):
        svc = BillingService()
        assert svc.cancel_subscription("nonexistent") is None

    def test_change_plan(self):
        svc = BillingService()
        svc.create_subscription("u1", "free")
        sub = svc.change_plan("u1", "pro")
        assert sub.plan_id == "pro"

    def test_change_plan_no_subscription(self):
        svc = BillingService()
        with pytest.raises(ValueError):
            svc.change_plan("u1", "pro")

    def test_credit_balance(self):
        svc = BillingService()
        balance = svc.get_credit_balance("u1")
        assert balance.get_balance("image") == 0.0

    def test_add_credits(self):
        svc = BillingService()
        new_balance = svc.add_credits("u1", "image", 100)
        assert new_balance == 100.0

    def test_consume_credits_success(self):
        svc = BillingService()
        svc.add_credits("u1", "image", 100)
        assert svc.consume_credits("u1", "image", 30) is True
        balance = svc.get_credit_balance("u1")
        assert balance.get_balance("image") == 70.0

    def test_consume_credits_insufficient(self):
        svc = BillingService()
        assert svc.consume_credits("u1", "image", 100) is False

    def test_create_invoice(self):
        svc = BillingService()
        items = [InvoiceItem(description="Pro plan", quantity=1, unit_price=29.99, total=29.99)]
        invoice = svc.create_invoice("u1", items)
        assert invoice.subtotal == 29.99
        assert invoice.status == InvoiceStatus.PENDING

    def test_pay_invoice(self):
        svc = BillingService()
        items = [InvoiceItem(description="Pro plan", quantity=1, unit_price=29.99, total=29.99)]
        invoice = svc.create_invoice("u1", items)
        paid = svc.pay_invoice(invoice.id)
        assert paid.status == InvoiceStatus.PAID
        assert paid.paid_at is not None

    def test_get_invoices(self):
        svc = BillingService()
        items = [InvoiceItem(description="Item", quantity=1, unit_price=10, total=10)]
        svc.create_invoice("u1", items)
        svc.create_invoice("u2", items)
        assert len(svc.get_invoices()) == 2
        assert len(svc.get_invoices(user_id="u1")) == 1

    def test_check_plan_limits(self):
        svc = BillingService()
        svc.create_subscription("u1", "free")
        assert svc.check_plan_limits("u1", "images", 50) is True
        assert svc.check_plan_limits("u1", "images", 200) is False


# ===========================================================================
# Cost Analytics Tests
# ===========================================================================
class TestCostAnalyticsService:
    def test_record_cost(self):
        svc = CostAnalyticsService()
        svc.record_cost(user_id="u1", project_id="p1", provider="gemini", cost_usd=0.05)
        assert svc.entry_count == 1

    def test_get_breakdown(self):
        svc = CostAnalyticsService()
        svc.record_cost(user_id="u1", project_id="p1", provider="gemini", cost_usd=0.05)
        svc.record_cost(user_id="u2", project_id="p2", provider="veo", cost_usd=0.50)
        breakdown = svc.get_breakdown()
        assert breakdown.total_cost == 0.55
        assert "p1" in breakdown.cost_per_project
        assert "u1" in breakdown.cost_per_user
        assert "gemini" in breakdown.cost_per_provider

    def test_get_breakdown_with_revenue(self):
        svc = CostAnalyticsService()
        svc.record_cost(user_id="u1", cost_usd=10.0)
        breakdown = svc.get_breakdown(revenue=50.0)
        assert breakdown.profit_margin == 80.0

    def test_get_project_cost(self):
        svc = CostAnalyticsService()
        svc.record_cost(project_id="p1", cost_usd=5.0)
        svc.record_cost(project_id="p1", cost_usd=3.0)
        assert svc.get_project_cost("p1") == 8.0

    def test_get_user_cost(self):
        svc = CostAnalyticsService()
        svc.record_cost(user_id="u1", cost_usd=5.0)
        assert svc.get_user_cost("u1") == 5.0

    def test_get_daily_costs(self):
        svc = CostAnalyticsService()
        svc.record_cost(user_id="u1", cost_usd=5.0)
        daily = svc.get_daily_costs(days=7)
        assert len(daily) >= 1

    def test_get_monthly_costs(self):
        svc = CostAnalyticsService()
        svc.record_cost(user_id="u1", cost_usd=5.0)
        monthly = svc.get_monthly_costs(months=3)
        assert len(monthly) >= 1

    def test_clear(self):
        svc = CostAnalyticsService()
        svc.record_cost(cost_usd=1.0)
        svc.clear()
        assert svc.entry_count == 0


# ===========================================================================
# Organization Service Tests
# ===========================================================================
class TestOrganizationService:
    def test_create_organization(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        assert org.name == "My Org"
        assert org.owner_id == "owner1"
        assert org.member_count == 1

    def test_get_organization(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        result = svc.get_organization(org.id)
        assert result is not None

    def test_get_organization_by_slug(self):
        svc = OrganizationService()
        svc.create_organization("My Org", "owner1", slug="my-org")
        result = svc.get_organization_by_slug("my-org")
        assert result is not None

    def test_list_organizations(self):
        svc = OrganizationService()
        svc.create_organization("Org 1", "owner1")
        svc.create_organization("Org 2", "owner2")
        assert len(svc.list_organizations()) == 2

    def test_list_organizations_by_user(self):
        svc = OrganizationService()
        svc.create_organization("Org 1", "owner1")
        svc.create_organization("Org 2", "owner2")
        assert len(svc.list_organizations(user_id="owner1")) == 1

    def test_add_member(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        member = svc.add_member(org.id, "user2", OrgRole.MEMBER)
        assert member is not None
        assert member.role == OrgRole.MEMBER
        assert org.member_count == 2

    def test_add_member_already_exists(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        result = svc.add_member(org.id, "owner1")
        assert result is None

    def test_add_member_exceeds_max(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1", max_members=1)
        result = svc.add_member(org.id, "user2")
        assert result is None

    def test_remove_member(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        svc.add_member(org.id, "user2")
        assert svc.remove_member(org.id, "user2") is True
        assert org.member_count == 1

    def test_remove_owner_fails(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        assert svc.remove_member(org.id, "owner1") is False

    def test_update_member_role(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        svc.add_member(org.id, "user2", OrgRole.MEMBER)
        member = svc.update_member_role(org.id, "user2", OrgRole.ADMIN)
        assert member.role == OrgRole.ADMIN

    def test_transfer_ownership(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        svc.add_member(org.id, "user2", OrgRole.MEMBER)
        assert svc.transfer_ownership(org.id, "user2") is True
        assert org.owner_id == "user2"

    def test_transfer_ownership_non_member(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        assert svc.transfer_ownership(org.id, "nonexistent") is False

    def test_create_invitation(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        inv = svc.create_invitation(org.id, "user2@example.com", OrgRole.MEMBER, invited_by="owner1")
        assert inv is not None
        assert inv.status == InvitationStatus.PENDING
        assert inv.token != ""

    def test_accept_invitation(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1", max_members=10)
        inv = svc.create_invitation(org.id, "user2@example.com", invited_by="owner1")
        member = svc.accept_invitation(inv.id, "user2")
        assert member is not None
        assert inv.status == InvitationStatus.ACCEPTED

    def test_decline_invitation(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        inv = svc.create_invitation(org.id, "user2@example.com")
        assert svc.decline_invitation(inv.id) is True
        assert inv.status == InvitationStatus.DECLINED

    def test_revoke_invitation(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        inv = svc.create_invitation(org.id, "user2@example.com")
        assert svc.revoke_invitation(inv.id) is True
        assert inv.status == InvitationStatus.REVOKED

    def test_share_project(self):
        svc = OrganizationService()
        share = svc.share_project("p1", "u1", "u2")
        assert share.project_id == "p1"
        assert share.shared_with == "u2"

    def test_get_project_shares(self):
        svc = OrganizationService()
        svc.share_project("p1", "u1", "u2")
        svc.share_project("p1", "u1", "u3")
        assert len(svc.get_project_shares("p1")) == 2

    def test_add_comment(self):
        svc = OrganizationService()
        comment = svc.add_comment("p1", "u1", "Great work!")
        assert comment.content == "Great work!"
        assert comment.resolved is False

    def test_resolve_comment(self):
        svc = OrganizationService()
        comment = svc.add_comment("p1", "u1", "Fix this")
        assert svc.resolve_comment(comment.id) is True
        assert comment.resolved is True

    def test_create_approval(self):
        svc = OrganizationService()
        approval = svc.create_approval("p1", "u1", "u2")
        assert approval.status == "pending"

    def test_resolve_approval(self):
        svc = OrganizationService()
        approval = svc.create_approval("p1", "u1", "u2")
        resolved = svc.resolve_approval(approval.id, "approved", "Looks good")
        assert resolved.status == "approved"
        assert resolved.resolved_at is not None

    def test_get_activity_feed(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        feed = svc.get_activity_feed(org.id)
        assert len(feed) >= 1

    def test_delete_organization(self):
        svc = OrganizationService()
        org = svc.create_organization("My Org", "owner1")
        assert svc.delete_organization(org.id) is True
        assert svc.get_organization(org.id) is None

    def test_org_count(self):
        svc = OrganizationService()
        svc.create_organization("Org 1", "owner1")
        assert svc.org_count == 1


# ===========================================================================
# Notification Service Tests
# ===========================================================================
class TestNotificationService:
    def test_send_in_app(self):
        svc = NotificationService()
        notif = svc.send("u1", "Welcome", "Welcome to the platform!")
        assert notif.user_id == "u1"
        assert notif.title == "Welcome"
        assert notif.channel == NotificationChannel.IN_APP

    def test_send_email(self):
        svc = NotificationService()
        notif = svc.send("u1", "Verify", "Please verify", channel=NotificationChannel.EMAIL)
        assert notif.channel == NotificationChannel.EMAIL

    def test_send_batch(self):
        svc = NotificationService()
        notifs = svc.send_batch(["u1", "u2", "u3"], "Update", "New features!")
        assert len(notifs) == 3

    def test_mark_read(self):
        svc = NotificationService()
        notif = svc.send("u1", "Test", "Body")
        assert svc.mark_read(notif.id) is True
        assert notif.status == NotificationStatus.READ

    def test_dismiss(self):
        svc = NotificationService()
        notif = svc.send("u1", "Test", "Body")
        assert svc.dismiss(notif.id) is True
        assert notif.status == NotificationStatus.DISMISSED

    def test_get_notifications(self):
        svc = NotificationService()
        svc.send("u1", "N1", "B1")
        svc.send("u1", "N2", "B2")
        svc.send("u2", "N3", "B3")
        notifs = svc.get_notifications("u1")
        assert len(notifs) == 2

    def test_get_unread_count(self):
        svc = NotificationService()
        svc.send("u1", "N1", "B1")
        svc.send("u1", "N2", "B2")
        assert svc.get_unread_count("u1") == 2

    def test_register_webhook(self):
        svc = NotificationService()
        webhook = svc.register_webhook("org1", "https://example.com/webhook", ["project.created"])
        assert webhook.url == "https://example.com/webhook"
        assert webhook.is_active is True

    def test_get_webhooks(self):
        svc = NotificationService()
        svc.register_webhook("org1", "https://example.com/wh1", ["event1"])
        svc.register_webhook("org1", "https://example.com/wh2", ["event2"])
        assert len(svc.get_webhooks("org1")) == 2

    def test_delete_webhook(self):
        svc = NotificationService()
        webhook = svc.register_webhook("org1", "https://example.com/wh", ["event1"])
        assert svc.delete_webhook(webhook.id) is True

    def test_notification_count(self):
        svc = NotificationService()
        svc.send("u1", "Test", "Body")
        assert svc.notification_count == 1

    def test_clear(self):
        svc = NotificationService()
        svc.send("u1", "Test", "Body")
        svc.clear()
        assert svc.notification_count == 0


# ===========================================================================
# Feature Flag Service Tests
# ===========================================================================
class TestFeatureFlagService:
    def test_create_flag(self):
        svc = FeatureFlagService()
        flag = FeatureFlag(key="new_ui", name="New UI", enabled=True)
        svc.create_flag(flag)
        assert svc.get_flag("new_ui") is not None

    def test_create_flag_duplicate(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="test", name="Test", enabled=True))
        with pytest.raises(ValueError):
            svc.create_flag(FeatureFlag(key="test", name="Test2", enabled=True))

    def test_is_enabled_global(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="global_flag", name="Global", enabled=True, scope=FeatureFlagScope.GLOBAL))
        assert svc.is_enabled("global_flag") is True

    def test_is_enabled_disabled(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="disabled", name="Disabled", enabled=False))
        assert svc.is_enabled("disabled") is False

    def test_is_enabled_user_scope(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(
            key="beta_feature",
            name="Beta",
            enabled=True,
            scope=FeatureFlagScope.USER,
            user_ids=["u1", "u2"],
        ))
        assert svc.is_enabled("beta_feature", user_id="u1") is True
        assert svc.is_enabled("beta_feature", user_id="u3") is False

    def test_is_enabled_org_scope(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(
            key="org_feature",
            name="Org Feature",
            enabled=True,
            scope=FeatureFlagScope.ORGANIZATION,
            org_ids=["org1"],
        ))
        assert svc.is_enabled("org_feature", org_id="org1") is True
        assert svc.is_enabled("org_feature", org_id="org2") is False

    def test_enable_for_user(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="flag", name="Flag", enabled=True, scope=FeatureFlagScope.USER))
        assert svc.enable_for_user("flag", "u1") is True
        assert svc.is_enabled("flag", user_id="u1") is True

    def test_disable_for_user(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="flag", name="Flag", enabled=True, scope=FeatureFlagScope.USER, user_ids=["u1"]))
        assert svc.disable_for_user("flag", "u1") is True
        assert svc.is_enabled("flag", user_id="u1") is False

    def test_enable_for_org(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="flag", name="Flag", enabled=True, scope=FeatureFlagScope.ORGANIZATION))
        assert svc.enable_for_org("flag", "org1") is True
        assert svc.is_enabled("flag", org_id="org1") is True

    def test_update_flag(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="flag", name="Flag", enabled=False))
        updated = svc.update_flag("flag", enabled=True)
        assert updated.enabled is True

    def test_delete_flag(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="flag", name="Flag"))
        assert svc.delete_flag("flag") is True
        assert svc.get_flag("flag") is None

    def test_list_flags(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="f1", name="F1", scope=FeatureFlagScope.GLOBAL))
        svc.create_flag(FeatureFlag(key="f2", name="F2", scope=FeatureFlagScope.USER))
        assert len(svc.list_flags()) == 2
        assert len(svc.list_flags(scope=FeatureFlagScope.GLOBAL)) == 1

    def test_get_variant(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(
            key="ab_test",
            name="A/B Test",
            flag_type=FeatureFlagType.VARIANT,
            enabled=True,
            variants={"control": {}, "treatment": {}},
        ))
        variant = svc.get_variant("ab_test", user_id="u1")
        assert variant in ("control", "treatment")

    def test_get_variant_not_variant_type(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="bool_flag", name="Bool", flag_type=FeatureFlagType.BOOLEAN))
        assert svc.get_variant("bool_flag") is None

    def test_flag_count(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="f1", name="F1"))
        assert svc.flag_count == 1

    def test_clear(self):
        svc = FeatureFlagService()
        svc.create_flag(FeatureFlag(key="f1", name="F1"))
        svc.clear()
        assert svc.flag_count == 0


# ===========================================================================
# Platform Audit Service Tests
# ===========================================================================
class TestPlatformAuditService:
    def test_record(self):
        svc = PlatformAuditService()
        entry = svc.record(
            user_id="u1",
            action=PlatformAuditAction.PUBLISHING,
            resource_type="video",
            resource_id="v1",
        )
        assert entry.action == PlatformAuditAction.PUBLISHING
        assert entry.user_id == "u1"

    def test_get_entries(self):
        svc = PlatformAuditService()
        svc.record(user_id="u1", action=PlatformAuditAction.GENERATION)
        svc.record(user_id="u2", action=PlatformAuditAction.DELETION)
        entries = svc.get_entries()
        assert len(entries) == 2

    def test_get_entries_filter_by_user(self):
        svc = PlatformAuditService()
        svc.record(user_id="u1", action=PlatformAuditAction.GENERATION)
        svc.record(user_id="u2", action=PlatformAuditAction.DELETION)
        entries = svc.get_entries(user_id="u1")
        assert len(entries) == 1
        assert entries[0].user_id == "u1"

    def test_get_entries_filter_by_action(self):
        svc = PlatformAuditService()
        svc.record(user_id="u1", action=PlatformAuditAction.GENERATION)
        svc.record(user_id="u2", action=PlatformAuditAction.DELETION)
        entries = svc.get_entries(action=PlatformAuditAction.GENERATION)
        assert len(entries) == 1

    def test_get_user_history(self):
        svc = PlatformAuditService()
        svc.record(user_id="u1", action=PlatformAuditAction.GENERATION)
        svc.record(user_id="u1", action=PlatformAuditAction.PUBLISHING)
        history = svc.get_user_history("u1")
        assert len(history) == 2

    def test_get_resource_history(self):
        svc = PlatformAuditService()
        svc.record(user_id="u1", action=PlatformAuditAction.GENERATION, resource_type="project", resource_id="p1")
        svc.record(user_id="u2", action=PlatformAuditAction.DELETION, resource_type="project", resource_id="p1")
        history = svc.get_resource_history("project", "p1")
        assert len(history) == 2

    def test_count_by_action(self):
        svc = PlatformAuditService()
        svc.record(action=PlatformAuditAction.GENERATION)
        svc.record(action=PlatformAuditAction.GENERATION)
        svc.record(action=PlatformAuditAction.DELETION)
        counts = svc.count_by_action()
        assert counts["generation"] == 2
        assert counts["deletion"] == 1

    def test_entry_count(self):
        svc = PlatformAuditService()
        svc.record(action=PlatformAuditAction.GENERATION)
        assert svc.entry_count == 1

    def test_clear(self):
        svc = PlatformAuditService()
        svc.record(action=PlatformAuditAction.GENERATION)
        svc.clear()
        assert svc.entry_count == 0


# ===========================================================================
# Monitoring Service Tests
# ===========================================================================
class TestMonitoringService:
    def test_record_metric(self):
        svc = MonitoringService()
        svc.record_metric(MonitoringMetric(name="latency", value=50.0, unit="ms"))
        assert svc.metric_count == 1

    def test_record_latency(self):
        svc = MonitoringService()
        svc.record_latency("api", 25.5)
        metrics = svc.get_metrics(name="latency")
        assert len(metrics) == 1
        assert metrics[0].value == 25.5

    def test_record_queue_size(self):
        svc = MonitoringService()
        svc.record_queue_size("generation", 15)
        metrics = svc.get_metrics(name="queue_size")
        assert len(metrics) == 1

    def test_record_failure(self):
        svc = MonitoringService()
        svc.record_failure("api", "timeout")
        metrics = svc.get_metrics(name="failure")
        assert len(metrics) == 1

    def test_record_provider_availability(self):
        svc = MonitoringService()
        svc.record_provider_availability("gemini", True)
        svc.record_provider_availability("veo", False)
        metrics = svc.get_metrics(name="provider_availability")
        assert len(metrics) == 2

    def test_record_resource_usage(self):
        svc = MonitoringService()
        svc.record_resource_usage(memory_mb=512, cpu_percent=45, disk_percent=70)
        assert svc.metric_count == 3

    def test_take_snapshot(self):
        svc = MonitoringService()
        svc.record_latency("api", 50)
        svc.record_failure("api")
        snapshot = svc.take_snapshot()
        assert snapshot.latency_ms == 50
        assert snapshot.failure_count == 1

    def test_get_latest_snapshot(self):
        svc = MonitoringService()
        svc.take_snapshot()
        assert svc.get_latest_snapshot() is not None

    def test_get_latest_snapshot_empty(self):
        svc = MonitoringService()
        assert svc.get_latest_snapshot() is None

    def test_clear(self):
        svc = MonitoringService()
        svc.record_latency("api", 50)
        svc.clear()
        assert svc.metric_count == 0


# ===========================================================================
# Health Service Tests
# ===========================================================================
class TestHealthService:
    def test_register_check(self):
        svc = HealthService()
        svc.register_check("database", lambda: HealthCheck(component="database", status=HealthStatus.HEALTHY))
        assert svc.component_count == 1

    def test_check_component(self):
        svc = HealthService()
        svc.register_check("db", lambda: HealthCheck(component="db", status=HealthStatus.HEALTHY, latency_ms=5))
        result = svc.check_component("db")
        assert result.status == HealthStatus.HEALTHY
        assert result.latency_ms == 5

    def test_check_component_not_registered(self):
        svc = HealthService()
        result = svc.check_component("nonexistent")
        assert result.status == HealthStatus.UNKNOWN

    def test_check_all_healthy(self):
        svc = HealthService()
        svc.register_check("db", lambda: HealthCheck(component="db", status=HealthStatus.HEALTHY))
        svc.register_check("redis", lambda: HealthCheck(component="redis", status=HealthStatus.HEALTHY))
        report = svc.check_all()
        assert report.overall_status == HealthStatus.HEALTHY
        assert report.healthy_count == 2

    def test_check_all_unhealthy(self):
        svc = HealthService()
        svc.register_check("db", lambda: HealthCheck(component="db", status=HealthStatus.HEALTHY))
        svc.register_check("redis", lambda: HealthCheck(component="redis", status=HealthStatus.UNHEALTHY))
        report = svc.check_all()
        assert report.overall_status == HealthStatus.UNHEALTHY

    def test_check_all_degraded(self):
        svc = HealthService()
        svc.register_check("db", lambda: HealthCheck(component="db", status=HealthStatus.HEALTHY))
        svc.register_check("redis", lambda: HealthCheck(component="redis", status=HealthStatus.DEGRADED))
        report = svc.check_all()
        assert report.overall_status == HealthStatus.DEGRADED

    def test_is_healthy(self):
        svc = HealthService()
        svc.register_check("db", lambda: HealthCheck(component="db", status=HealthStatus.HEALTHY))
        assert svc.is_healthy() is True

    def test_unregister_check(self):
        svc = HealthService()
        svc.register_check("db", lambda: HealthCheck(component="db", status=HealthStatus.HEALTHY))
        svc.unregister_check("db")
        assert svc.component_count == 0

    def test_registered_components(self):
        svc = HealthService()
        svc.register_check("db", lambda: HealthCheck(component="db", status=HealthStatus.HEALTHY))
        svc.register_check("redis", lambda: HealthCheck(component="redis", status=HealthStatus.HEALTHY))
        assert "db" in svc.registered_components
        assert "redis" in svc.registered_components


# ===========================================================================
# Metrics Service Tests
# ===========================================================================
class TestMetricsService:
    def test_record(self):
        svc = MetricsService()
        svc.record(Metric(name="projects_created", category=MetricCategory.BUSINESS, value=10))
        assert svc.metric_count == 1

    def test_record_business(self):
        svc = MetricsService()
        svc.record_business("projects", 5)
        metrics = svc.get_metrics(category=MetricCategory.BUSINESS)
        assert len(metrics) == 1

    def test_record_technical(self):
        svc = MetricsService()
        svc.record_technical("cpu", 45.5, unit="%")
        metrics = svc.get_metrics(category=MetricCategory.TECHNICAL)
        assert len(metrics) == 1

    def test_record_performance(self):
        svc = MetricsService()
        svc.record_performance("latency", 50, unit="ms")
        metrics = svc.get_metrics(category=MetricCategory.PERFORMANCE)
        assert len(metrics) == 1

    def test_record_financial(self):
        svc = MetricsService()
        svc.record_financial("revenue", 1000)
        metrics = svc.get_metrics(category=MetricCategory.FINANCIAL)
        assert len(metrics) == 1

    def test_record_operational(self):
        svc = MetricsService()
        svc.record_operational("queue_size", 25)
        metrics = svc.get_metrics(category=MetricCategory.OPERATIONAL)
        assert len(metrics) == 1

    def test_get_summary(self):
        svc = MetricsService()
        svc.record_business("projects", 5)
        svc.record_business("projects", 3)
        svc.record_financial("revenue", 100)
        summary = svc.get_summary()
        assert summary.business["projects"] == 8
        assert summary.financial["revenue"] == 100

    def test_get_metrics_by_name(self):
        svc = MetricsService()
        svc.record_business("projects", 5)
        svc.record_business("users", 10)
        metrics = svc.get_metrics(name="projects")
        assert len(metrics) == 1

    def test_get_metric_names(self):
        svc = MetricsService()
        svc.record_business("projects", 5)
        svc.record_business("users", 10)
        names = svc.get_metric_names()
        assert "projects" in names
        assert "users" in names

    def test_clear(self):
        svc = MetricsService()
        svc.record_business("projects", 5)
        svc.clear()
        assert svc.metric_count == 0


# ===========================================================================
# API Management Service Tests
# ===========================================================================
class TestApiManagementService:
    def test_create_api_key(self):
        svc = ApiManagementService()
        key_info, key_string = svc.create_api_key("u1", "My Key")
        assert key_info.name == "My Key"
        assert key_string.startswith("sk_")
        assert key_info.is_active is True

    def test_get_api_key(self):
        svc = ApiManagementService()
        key_info, _ = svc.create_api_key("u1", "My Key")
        result = svc.get_api_key(key_info.id)
        assert result is not None

    def test_get_api_key_by_value(self):
        svc = ApiManagementService()
        key_info, key_string = svc.create_api_key("u1", "My Key")
        result = svc.get_api_key_by_value(key_string)
        assert result is not None
        assert result.id == key_info.id

    def test_list_api_keys(self):
        svc = ApiManagementService()
        svc.create_api_key("u1", "Key 1")
        svc.create_api_key("u1", "Key 2")
        svc.create_api_key("u2", "Key 3")
        assert len(svc.list_api_keys("u1")) == 2
        assert len(svc.list_api_keys("u2")) == 1

    def test_revoke_api_key(self):
        svc = ApiManagementService()
        key_info, _ = svc.create_api_key("u1", "My Key")
        assert svc.revoke_api_key(key_info.id) is True
        assert key_info.is_active is False

    def test_delete_api_key(self):
        svc = ApiManagementService()
        key_info, _ = svc.create_api_key("u1", "My Key")
        assert svc.delete_api_key(key_info.id) is True
        assert svc.get_api_key(key_info.id) is None

    def test_check_rate_limit(self):
        svc = ApiManagementService()
        svc.set_rate_limit("u1", RateLimitConfig(requests_per_minute=5, requests_per_day=100))
        for _ in range(5):
            assert svc.check_rate_limit("u1") is True
        assert svc.check_rate_limit("u1") is False

    def test_set_rate_limit(self):
        svc = ApiManagementService()
        svc.set_rate_limit("u1", RateLimitConfig(requests_per_minute=100))
        config = svc.get_rate_limit("u1")
        assert config.requests_per_minute == 100

    def test_set_quota(self):
        svc = ApiManagementService()
        quota = svc.set_quota("u1", UsageResourceType.IMAGES, 100)
        assert quota.limit == 100
        assert quota.used == 0

    def test_get_quota(self):
        svc = ApiManagementService()
        svc.set_quota("u1", UsageResourceType.IMAGES, 100)
        quota = svc.get_quota("u1", UsageResourceType.IMAGES)
        assert quota is not None
        assert quota.limit == 100

    def test_record_quota_usage(self):
        svc = ApiManagementService()
        svc.set_quota("u1", UsageResourceType.IMAGES, 100)
        quota = svc.record_quota_usage("u1", UsageResourceType.IMAGES, 30)
        assert quota.used == 30
        assert quota.remaining == 70

    def test_check_quota(self):
        svc = ApiManagementService()
        svc.set_quota("u1", UsageResourceType.IMAGES, 100)
        svc.record_quota_usage("u1", UsageResourceType.IMAGES, 90)
        assert svc.check_quota("u1", UsageResourceType.IMAGES, 5) is True
        assert svc.check_quota("u1", UsageResourceType.IMAGES, 20) is False

    def test_check_quota_no_quota(self):
        svc = ApiManagementService()
        assert svc.check_quota("u1", UsageResourceType.IMAGES, 100) is True

    def test_get_usage_report(self):
        svc = ApiManagementService()
        svc.create_api_key("u1", "My Key")
        svc.set_quota("u1", UsageResourceType.IMAGES, 100)
        report = svc.get_usage_report("u1")
        assert "api_keys" in report
        assert "quotas" in report

    def test_api_key_count(self):
        svc = ApiManagementService()
        svc.create_api_key("u1", "Key 1")
        assert svc.api_key_count == 1


# ===========================================================================
# Admin Service Tests
# ===========================================================================
class TestAdminService:
    def test_get_platform_overview(self):
        analytics = AnalyticsService()
        usage = UsageTracker()
        billing = BillingService()
        monitoring = MonitoringService()
        health = HealthService()
        audit = PlatformAuditService()

        admin = AdminService(
            analytics_service=analytics,
            usage_tracker=usage,
            billing_service=billing,
            monitoring_service=monitoring,
            health_service=health,
            audit_service=audit,
        )

        overview = admin.get_platform_overview()
        assert "timestamp" in overview
        assert "analytics" in overview
        assert "billing" in overview

    def test_get_user_overview(self):
        usage = UsageTracker()
        billing = BillingService()
        analytics = AnalyticsService()

        admin = AdminService(
            analytics_service=analytics,
            usage_tracker=usage,
            billing_service=billing,
        )

        overview = admin.get_user_overview("u1")
        assert overview["user_id"] == "u1"
        assert "usage" in overview

    def test_get_system_health(self):
        health = HealthService()
        health.register_check("db", lambda: HealthCheck(component="db", status=HealthStatus.HEALTHY))

        admin = AdminService(health_service=health)
        result = admin.get_system_health()
        assert result["overall_status"] == "healthy"

    def test_get_billing_overview(self):
        billing = BillingService()
        admin = AdminService(billing_service=billing)
        result = admin.get_billing_overview()
        assert "total_invoices" in result
        assert "plans" in result

    def test_get_recent_logs(self):
        audit = PlatformAuditService()
        audit.record(user_id="u1", action=PlatformAuditAction.GENERATION)

        admin = AdminService(audit_service=audit)
        logs = admin.get_recent_logs()
        assert len(logs) == 1

    def test_suspend_user(self):
        audit = PlatformAuditService()
        admin = AdminService(audit_service=audit)
        assert admin.suspend_user("u1") is True
        assert audit.entry_count == 1

    def test_activate_user(self):
        audit = PlatformAuditService()
        admin = AdminService(audit_service=audit)
        assert admin.activate_user("u1") is True
        assert audit.entry_count == 1

    def test_get_provider_health(self):
        monitoring = MonitoringService()
        monitoring.record_provider_availability("gemini", True)
        monitoring.take_snapshot()

        admin = AdminService(monitoring_service=monitoring)
        result = admin.get_provider_health()
        assert "provider_availability" in result

    def test_platform_overview_empty(self):
        admin = AdminService()
        overview = admin.get_platform_overview()
        assert "timestamp" in overview


# ===========================================================================
# Integration Tests
# ===========================================================================
class TestIntegration:
    def test_full_platform_workflow(self):
        """Test a full platform workflow with multiple services."""
        # Initialize services
        analytics = AnalyticsService()
        usage = UsageTracker()
        billing = BillingService()
        cost_analytics = CostAnalyticsService()
        org_svc = OrganizationService()
        notifications = NotificationService()
        flags = FeatureFlagService()
        audit = PlatformAuditService()
        monitoring = MonitoringService()
        health = HealthService()
        metrics = MetricsService()
        api_mgmt = ApiManagementService()

        # 1. Create organization
        org = org_svc.create_organization("My Company", "owner1")
        assert org.member_count == 1

        # 2. Invite and add member
        inv = org_svc.create_invitation(org.id, "user2@example.com", invited_by="owner1")
        member = org_svc.accept_invitation(inv.id, "user2")
        assert member is not None
        assert org.member_count == 2

        # 3. Create subscription
        sub = billing.create_subscription("owner1", "pro")
        assert sub.is_active is True

        # 4. Add credits
        billing.add_credits("owner1", "image", 500)

        # 5. Record usage
        usage.record_image_generation("owner1", count=10)
        usage.record_video_generation("owner1", count=2)
        usage.record_tokens("owner1", 50000)

        # 6. Record analytics
        analytics.record(ProjectAnalytics(
            project_id="p1",
            user_id="owner1",
            generation_time_seconds=120,
            success=True,
            provider="gemini",
            model="gemini-2.0-flash",
        ))

        # 7. Record cost
        cost_analytics.record_cost(
            user_id="owner1",
            project_id="p1",
            provider="gemini",
            cost_usd=0.25,
        )

        # 8. Create feature flag
        flags.create_flag(FeatureFlag(
            key="new_analytics",
            name="New Analytics Dashboard",
            enabled=True,
            scope=FeatureFlagScope.ORGANIZATION,
            org_ids=[str(org.id)],
        ))
        assert flags.is_enabled("new_analytics", org_id=str(org.id)) is True

        # 9. Send notification
        notif = notifications.send("owner1", "Project Complete", "Your video is ready!")
        assert notif.status in (NotificationStatus.PENDING, NotificationStatus.SENT)

        # 10. Record audit
        audit.record(
            user_id="owner1",
            action=PlatformAuditAction.PUBLISHING,
            resource_type="video",
            resource_id="v1",
        )

        # 11. Record monitoring metrics
        monitoring.record_latency("api", 45)
        monitoring.record_provider_availability("gemini", True)
        snapshot = monitoring.take_snapshot()
        assert snapshot.latency_ms == 45

        # 12. Register health check
        health.register_check("db", lambda: HealthCheck(component="db", status=HealthStatus.HEALTHY))
        report = health.check_all()
        assert report.overall_status == HealthStatus.HEALTHY

        # 13. Record metrics
        metrics.record_business("projects_created", 1)
        metrics.record_financial("revenue", 29.99)

        # 14. Create API key
        key_info, key_string = api_mgmt.create_api_key("owner1", "Production Key")
        assert key_info.is_active is True

        # 15. Set quota
        api_mgmt.set_quota("owner1", UsageResourceType.IMAGES, 1000)

        # 16. Verify admin overview
        admin = AdminService(
            analytics_service=analytics,
            usage_tracker=usage,
            billing_service=billing,
            monitoring_service=monitoring,
            health_service=health,
            audit_service=audit,
        )
        overview = admin.get_platform_overview()
        assert overview["analytics"]["total_projects"] == 1
        assert overview["health"]["overall_status"] == "healthy"

    def test_billing_and_usage_integration(self):
        """Test billing and usage tracking integration."""
        billing = BillingService()
        usage = UsageTracker()

        # Create subscription
        billing.create_subscription("u1", "pro")

        # Record usage
        for _ in range(50):
            usage.record_image_generation("u1", count=1)

        summary = usage.get_summary("u1")
        assert summary.images_generated == 50

        # Check plan limits
        assert billing.check_plan_limits("u1", "images", 50) is True
        assert billing.check_plan_limits("u1", "images", 1001) is False

    def test_org_and_notifications_integration(self):
        """Test organization and notification integration."""
        org_svc = OrganizationService()
        notifications = NotificationService()

        # Create org and add members
        org = org_svc.create_organization("Test Org", "owner1")
        org_svc.add_member(org.id, "user2")
        org_svc.add_member(org.id, "user3")

        # Notify all members
        members = org_svc.get_members(org.id)
        user_ids = [m.user_id for m in members]
        notifs = notifications.send_batch(user_ids, "Org Update", "New policy!")

        assert len(notifs) == 3
        for n in notifs:
            assert n.title == "Org Update"
