"""Platform service — unifies analytics, billing, usage, orgs, feature flags, and admin.

This service wraps the existing platform subsystems into a single API-facing
service for Phase 5 (Platform Experience).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.core.exceptions import EntityNotFoundError, ValidationError
from src.core.logging import get_logger
from src.platform.analytics import AnalyticsService
from src.platform.billing import BillingService
from src.platform.cost_analytics import CostAnalyticsService
from src.platform.feature_flags import FeatureFlagService
from src.platform.monitoring import HealthService, MonitoringService
from src.platform.organization import OrganizationService
from src.platform.usage import UsageTracker
from src.platform.audit import PlatformAuditService
from src.platform.admin import AdminService
from src.platform.schema import (
    CreditBalance,
    CreditType,
    FeatureFlag,
    FeatureFlagScope,
    FeatureFlagType,
    Invoice,
    InvoiceItem,
    Plan,
    Subscription,
    TeamMember,
    Organization,
    UsageSummary,
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class AnalyticsResponse(BaseModel):
    total_projects: int = 0
    successful_projects: int = 0
    failed_projects: int = 0
    avg_generation_time: float = 0.0
    avg_publishing_time: float = 0.0
    avg_rendering_time: float = 0.0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    most_used_providers: dict[str, int] = {}
    top_models: dict[str, int] = {}
    project_growth: list[dict[str, Any]] = []
    user_activity: dict[str, int] = {}


class CostBreakdownResponse(BaseModel):
    cost_per_project: dict[str, float] = {}
    cost_per_user: dict[str, float] = {}
    cost_per_provider: dict[str, float] = {}
    cost_per_asset: dict[str, float] = {}
    cost_per_workflow: dict[str, float] = {}
    daily_costs: dict[str, float] = {}
    monthly_costs: dict[str, float] = {}
    total_cost: float = 0.0
    revenue: float = 0.0
    profit_margin: float = 0.0


class UsageSummaryResponse(BaseModel):
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
    provider_usage: dict[str, int] = {}
    period_start: str | None = None
    period_end: str | None = None


class PlanResponse(BaseModel):
    id: str
    name: str
    plan_type: str
    price_monthly: float
    price_yearly: float
    currency: str
    features: dict[str, Any]
    is_active: bool
    description: str


class SubscriptionResponse(BaseModel):
    id: str
    user_id: str
    org_id: str
    plan_id: str
    plan_type: str
    status: str
    started_at: str
    current_period_start: str
    current_period_end: str | None = None
    cancelled_at: str | None = None
    trial_end: str | None = None


class CreditBalanceResponse(BaseModel):
    user_id: str
    org_id: str
    credits: dict[str, float]


class InvoiceResponse(BaseModel):
    id: str
    user_id: str
    org_id: str
    subscription_id: str | None = None
    status: str
    items: list[dict[str, Any]] = []
    subtotal: float
    tax: float
    total: float
    currency: str
    issued_at: str
    due_at: str | None = None
    paid_at: str | None = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    owner_id: str
    plan_type: str
    member_count: int
    max_members: int
    is_active: bool
    created_at: str


class TeamMemberResponse(BaseModel):
    id: str
    org_id: str
    user_id: str
    role: str
    joined_at: str
    invited_by: str
    is_active: bool


class FeatureFlagResponse(BaseModel):
    key: str
    name: str
    description: str
    flag_type: str
    scope: str
    enabled: bool
    percentage: float
    variants: dict[str, Any] = {}
    user_ids: list[str] = []
    org_ids: list[str] = []
    plan_types: list[str] = []
    created_at: str
    updated_at: str | None = None


class PlatformOverviewResponse(BaseModel):
    timestamp: str
    analytics: dict[str, Any] = {}
    usage: dict[str, Any] = {}
    billing: dict[str, Any] = {}
    monitoring: dict[str, Any] = {}
    health: dict[str, Any] = {}
    audit: dict[str, Any] = {}


class HealthReportResponse(BaseModel):
    overall_status: str
    checks: list[dict[str, Any]] = []
    checked_at: str


class MonitoringSnapshotResponse(BaseModel):
    latency_ms: float
    queue_size: int
    worker_count: int
    active_workers: int
    failure_count: int
    retry_count: int
    provider_availability: dict[str, float] = {}
    memory_usage_mb: float
    cpu_usage_percent: float
    disk_usage_percent: float
    timestamp: str


class AuditEntryResponse(BaseModel):
    id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    created_at: str


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _plan_to_response(plan: Plan) -> PlanResponse:
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        plan_type=plan.plan_type.value,
        price_monthly=plan.price_monthly,
        price_yearly=plan.price_yearly,
        currency=plan.currency,
        features=plan.features.model_dump(),
        is_active=plan.is_active,
        description=plan.description,
    )


def _sub_to_response(sub: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=str(sub.id),
        user_id=sub.user_id,
        org_id=sub.org_id,
        plan_id=sub.plan_id,
        plan_type=sub.plan_type.value,
        status=sub.status.value,
        started_at=sub.started_at.isoformat(),
        current_period_start=sub.current_period_start.isoformat(),
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
        cancelled_at=sub.cancelled_at.isoformat() if sub.cancelled_at else None,
        trial_end=sub.trial_end.isoformat() if sub.trial_end else None,
    )


def _credit_to_response(balance: CreditBalance) -> CreditBalanceResponse:
    return CreditBalanceResponse(
        user_id=balance.user_id,
        org_id=balance.org_id,
        credits=balance.credits,
    )


def _invoice_to_response(inv: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=str(inv.id),
        user_id=inv.user_id,
        org_id=inv.org_id,
        subscription_id=str(inv.subscription_id) if inv.subscription_id else None,
        status=inv.status.value,
        items=[item.model_dump() for item in inv.items],
        subtotal=inv.subtotal,
        tax=inv.tax,
        total=inv.total,
        currency=inv.currency,
        issued_at=inv.issued_at.isoformat(),
        due_at=inv.due_at.isoformat() if inv.due_at else None,
        paid_at=inv.paid_at.isoformat() if inv.paid_at else None,
    )


def _org_to_response(org: Organization) -> OrganizationResponse:
    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        owner_id=org.owner_id,
        plan_type=org.plan_type.value,
        member_count=org.member_count,
        max_members=org.max_members,
        is_active=org.is_active,
        created_at=org.created_at.isoformat(),
    )


def _member_to_response(m: TeamMember) -> TeamMemberResponse:
    return TeamMemberResponse(
        id=str(m.id),
        org_id=str(m.org_id),
        user_id=m.user_id,
        role=m.role.value,
        joined_at=m.joined_at.isoformat(),
        invited_by=m.invited_by,
        is_active=m.is_active,
    )


def _flag_to_response(flag: FeatureFlag) -> FeatureFlagResponse:
    return FeatureFlagResponse(
        key=flag.key,
        name=flag.name,
        description=flag.description,
        flag_type=flag.flag_type.value,
        scope=flag.scope.value,
        enabled=flag.enabled,
        percentage=flag.percentage,
        variants=flag.variants,
        user_ids=flag.user_ids,
        org_ids=flag.org_ids,
        plan_types=flag.plan_types,
        created_at=flag.created_at.isoformat(),
        updated_at=flag.updated_at.isoformat() if flag.updated_at else None,
    )


def _usage_to_response(summary: UsageSummary) -> UsageSummaryResponse:
    return UsageSummaryResponse(
        user_id=summary.user_id,
        org_id=summary.org_id,
        images_generated=summary.images_generated,
        videos_generated=summary.videos_generated,
        voice_minutes=summary.voice_minutes,
        rendering_minutes=summary.rendering_minutes,
        storage_bytes=summary.storage_bytes,
        bandwidth_bytes=summary.bandwidth_bytes,
        projects_created=summary.projects_created,
        publishing_count=summary.publishing_count,
        token_usage=summary.token_usage,
        provider_usage=summary.provider_usage,
        period_start=summary.period_start.isoformat() if summary.period_start else None,
        period_end=summary.period_end.isoformat() if summary.period_end else None,
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class PlatformService:
    """Unified platform service for analytics, billing, usage, orgs, flags, admin."""

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._analytics = AnalyticsService()
        self._cost_analytics = CostAnalyticsService()
        self._usage = UsageTracker()
        self._billing = BillingService()
        self._org = OrganizationService()
        self._flags = FeatureFlagService()
        self._audit = PlatformAuditService()
        self._monitoring = MonitoringService()
        self._health = HealthService()
        self._admin = AdminService(
            analytics_service=self._analytics,
            usage_tracker=self._usage,
            billing_service=self._billing,
            monitoring_service=self._monitoring,
            health_service=self._health,
            audit_service=self._audit,
        )

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------
    async def get_analytics_summary(
        self,
        *,
        user_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> AnalyticsResponse:
        start_dt = datetime.fromisoformat(start) if start else None
        end_dt = datetime.fromisoformat(end) if end else None
        summary = self._analytics.get_summary(user_id=user_id, start=start_dt, end=end_dt)
        return AnalyticsResponse(**summary.model_dump())

    async def get_cost_breakdown(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        revenue: float = 0.0,
    ) -> CostBreakdownResponse:
        start_dt = datetime.fromisoformat(start) if start else None
        end_dt = datetime.fromisoformat(end) if end else None
        breakdown = self._cost_analytics.get_breakdown(start=start_dt, end=end_dt, revenue=revenue)
        return CostBreakdownResponse(**breakdown.model_dump())

    # ------------------------------------------------------------------
    # Usage
    # ------------------------------------------------------------------
    async def get_usage_summary(self, user_id: str) -> UsageSummaryResponse:
        summary = self._usage.get_summary(user_id)
        return _usage_to_response(summary)

    # ------------------------------------------------------------------
    # Billing
    # ------------------------------------------------------------------
    async def list_plans(self) -> list[PlanResponse]:
        return [_plan_to_response(p) for p in self._billing.list_plans()]

    async def get_plan(self, plan_id: str) -> PlanResponse:
        plan = self._billing.get_plan(plan_id)
        if plan is None:
            raise EntityNotFoundError(f"Plan '{plan_id}' not found")
        return _plan_to_response(plan)

    async def get_subscription(self, user_id: str) -> SubscriptionResponse | None:
        sub = self._billing.get_subscription(user_id)
        if sub is None:
            return None
        return _sub_to_response(sub)

    async def create_subscription(
        self, user_id: str, plan_id: str, *, trial_days: int = 0
    ) -> SubscriptionResponse:
        sub = self._billing.create_subscription(user_id, plan_id, trial_days=trial_days)
        return _sub_to_response(sub)

    async def cancel_subscription(self, user_id: str) -> SubscriptionResponse | None:
        sub = self._billing.cancel_subscription(user_id)
        if sub is None:
            return None
        return _sub_to_response(sub)

    async def change_plan(self, user_id: str, new_plan_id: str) -> SubscriptionResponse:
        sub = self._billing.change_plan(user_id, new_plan_id)
        return _sub_to_response(sub)

    async def get_credit_balance(self, user_id: str) -> CreditBalanceResponse:
        balance = self._billing.get_credit_balance(user_id)
        return _credit_to_response(balance)

    async def add_credits(self, user_id: str, credit_type: str, amount: float) -> CreditBalanceResponse:
        self._billing.add_credits(user_id, credit_type, amount)
        return await self.get_credit_balance(user_id)

    async def list_invoices(self, user_id: str | None = None) -> list[InvoiceResponse]:
        invoices = self._billing.get_invoices(user_id)
        return [_invoice_to_response(inv) for inv in invoices]

    async def pay_invoice(self, invoice_id: str) -> InvoiceResponse | None:
        inv = self._billing.pay_invoice(UUID(invoice_id))
        if inv is None:
            return None
        return _invoice_to_response(inv)

    # ------------------------------------------------------------------
    # Organizations
    # ------------------------------------------------------------------
    async def list_organizations(self, user_id: str | None = None) -> list[OrganizationResponse]:
        orgs = self._org.list_organizations(user_id)
        return [_org_to_response(o) for o in orgs]

    async def create_organization(
        self, name: str, owner_id: str, *, slug: str = "", max_members: int = 10
    ) -> OrganizationResponse:
        org = self._org.create_organization(name, owner_id, slug=slug, max_members=max_members)
        return _org_to_response(org)

    async def get_organization(self, org_id: str) -> OrganizationResponse:
        org = self._org.get_organization(UUID(org_id))
        if org is None:
            raise EntityNotFoundError(f"Organization {org_id} not found")
        return _org_to_response(org)

    async def list_members(self, org_id: str) -> list[TeamMemberResponse]:
        members = self._org.get_members(UUID(org_id))
        return [_member_to_response(m) for m in members]

    async def add_member(self, org_id: str, user_id: str, role: str = "member") -> TeamMemberResponse | None:
        from src.platform.schema import OrgRole
        org_role = OrgRole(role) if role in [r.value for r in OrgRole] else OrgRole.MEMBER
        member = self._org.add_member(UUID(org_id), user_id, role=org_role)
        if member is None:
            return None
        return _member_to_response(member)

    # ------------------------------------------------------------------
    # Feature Flags
    # ------------------------------------------------------------------
    async def list_feature_flags(self, scope: str | None = None) -> list[FeatureFlagResponse]:
        flag_scope = FeatureFlagScope(scope) if scope else None
        flags = self._flags.list_flags(scope=flag_scope)
        return [_flag_to_response(f) for f in flags]

    async def get_feature_flag(self, key: str) -> FeatureFlagResponse:
        flag = self._flags.get_flag(key)
        if flag is None:
            raise EntityNotFoundError(f"Feature flag '{key}' not found")
        return _flag_to_response(flag)

    async def create_feature_flag(
        self,
        key: str,
        name: str,
        *,
        description: str = "",
        flag_type: str = "boolean",
        scope: str = "global",
        enabled: bool = False,
        percentage: float = 100.0,
    ) -> FeatureFlagResponse:
        flag = FeatureFlag(
            key=key,
            name=name,
            description=description,
            flag_type=FeatureFlagType(flag_type),
            scope=FeatureFlagScope(scope),
            enabled=enabled,
            percentage=percentage,
        )
        created = self._flags.create_flag(flag)
        return _flag_to_response(created)

    async def update_feature_flag(self, key: str, **kwargs: Any) -> FeatureFlagResponse:
        flag = self._flags.update_flag(key, **kwargs)
        if flag is None:
            raise EntityNotFoundError(f"Feature flag '{key}' not found")
        return _flag_to_response(flag)

    async def delete_feature_flag(self, key: str) -> MessageResponse:
        deleted = self._flags.delete_flag(key)
        if not deleted:
            raise EntityNotFoundError(f"Feature flag '{key}' not found")
        return MessageResponse(message=f"Feature flag '{key}' deleted")

    async def is_feature_enabled(
        self, key: str, *, user_id: str = "", org_id: str = "", plan_type: str = ""
    ) -> bool:
        return self._flags.is_enabled(key, user_id=user_id, org_id=org_id, plan_type=plan_type)

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------
    async def get_platform_overview(self) -> PlatformOverviewResponse:
        overview = self._admin.get_platform_overview()
        return PlatformOverviewResponse(**overview)

    async def get_system_health(self) -> dict[str, Any]:
        return self._admin.get_system_health()

    async def get_provider_health(self) -> dict[str, Any]:
        return self._admin.get_provider_health()

    async def get_recent_audit_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._admin.get_recent_logs(limit=limit)

    async def get_billing_overview(self) -> dict[str, Any]:
        return self._admin.get_billing_overview()

    async def get_usage_dashboard(self) -> dict[str, Any]:
        return self._admin.get_usage_dashboard()

    async def suspend_user(self, user_id: str) -> MessageResponse:
        self._admin.suspend_user(user_id)
        return MessageResponse(message=f"User {user_id} suspended")

    async def activate_user(self, user_id: str) -> MessageResponse:
        self._admin.activate_user(user_id)
        return MessageResponse(message=f"User {user_id} activated")
