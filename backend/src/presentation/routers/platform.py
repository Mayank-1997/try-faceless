"""Platform router — analytics, billing, usage, orgs, feature flags, admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.application.services.authorization_service import require_authentication
from src.application.services.platform_service import (
    PlatformService,
    AnalyticsResponse,
    CostBreakdownResponse,
    UsageSummaryResponse,
    PlanResponse,
    SubscriptionResponse,
    CreditBalanceResponse,
    InvoiceResponse,
    OrganizationResponse,
    TeamMemberResponse,
    FeatureFlagResponse,
    PlatformOverviewResponse,
    HealthReportResponse,
    AuditEntryResponse,
    MessageResponse,
)

router = APIRouter(prefix="/platform", tags=["platform"])

_platform_service: PlatformService | None = None


def _get_platform_service() -> PlatformService:
    global _platform_service
    if _platform_service is None:
        _platform_service = PlatformService()
    return _platform_service


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
@router.get("/analytics/summary", response_model=AnalyticsResponse)
async def get_analytics_summary(
    user_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> AnalyticsResponse:
    return await service.get_analytics_summary(user_id=user_id, start=start, end=end)


@router.get("/analytics/costs", response_model=CostBreakdownResponse)
async def get_cost_breakdown(
    start: str | None = None,
    end: str | None = None,
    revenue: float = 0.0,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> CostBreakdownResponse:
    return await service.get_cost_breakdown(start=start, end=end, revenue=revenue)


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
@router.get("/usage/{user_id}", response_model=UsageSummaryResponse)
async def get_usage_summary(
    user_id: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> UsageSummaryResponse:
    return await service.get_usage_summary(user_id)


# ---------------------------------------------------------------------------
# Billing — Plans
# ---------------------------------------------------------------------------
@router.get("/billing/plans", response_model=list[PlanResponse])
async def list_plans(
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> list[PlanResponse]:
    return await service.list_plans()


@router.get("/billing/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> PlanResponse:
    return await service.get_plan(plan_id)


# ---------------------------------------------------------------------------
# Billing — Subscriptions
# ---------------------------------------------------------------------------
@router.get("/billing/subscriptions/{user_id}", response_model=SubscriptionResponse | None)
async def get_subscription(
    user_id: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> SubscriptionResponse | None:
    return await service.get_subscription(user_id)


@router.post("/billing/subscriptions", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    body: dict,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> SubscriptionResponse:
    return await service.create_subscription(
        body["user_id"], body["plan_id"], trial_days=body.get("trial_days", 0)
    )


@router.post("/billing/subscriptions/{user_id}/cancel", response_model=SubscriptionResponse | None)
async def cancel_subscription(
    user_id: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> SubscriptionResponse | None:
    return await service.cancel_subscription(user_id)


@router.patch("/billing/subscriptions/{user_id}", response_model=SubscriptionResponse)
async def change_plan(
    user_id: str,
    body: dict,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> SubscriptionResponse:
    return await service.change_plan(user_id, body["plan_id"])


# ---------------------------------------------------------------------------
# Billing — Credits
# ---------------------------------------------------------------------------
@router.get("/billing/credits/{user_id}", response_model=CreditBalanceResponse)
async def get_credit_balance(
    user_id: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> CreditBalanceResponse:
    return await service.get_credit_balance(user_id)


@router.post("/billing/credits/{user_id}/add", response_model=CreditBalanceResponse)
async def add_credits(
    user_id: str,
    body: dict,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> CreditBalanceResponse:
    return await service.add_credits(user_id, body["credit_type"], body["amount"])


# ---------------------------------------------------------------------------
# Billing — Invoices
# ---------------------------------------------------------------------------
@router.get("/billing/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    user_id: str | None = None,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> list[InvoiceResponse]:
    return await service.list_invoices(user_id)


@router.post("/billing/invoices/{invoice_id}/pay", response_model=InvoiceResponse | None)
async def pay_invoice(
    invoice_id: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> InvoiceResponse | None:
    return await service.pay_invoice(invoice_id)


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------
@router.get("/organizations", response_model=list[OrganizationResponse])
async def list_organizations(
    user_id: str | None = None,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> list[OrganizationResponse]:
    return await service.list_organizations(user_id)


@router.post("/organizations", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    body: dict,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> OrganizationResponse:
    return await service.create_organization(
        body["name"],
        body["owner_id"],
        slug=body.get("slug", ""),
        max_members=body.get("max_members", 10),
    )


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> OrganizationResponse:
    return await service.get_organization(org_id)


@router.get("/organizations/{org_id}/members", response_model=list[TeamMemberResponse])
async def list_members(
    org_id: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> list[TeamMemberResponse]:
    return await service.list_members(org_id)


@router.post("/organizations/{org_id}/members", response_model=TeamMemberResponse | None, status_code=201)
async def add_member(
    org_id: str,
    body: dict,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> TeamMemberResponse | None:
    return await service.add_member(org_id, body["user_id"], body.get("role", "member"))


# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------
@router.get("/feature-flags", response_model=list[FeatureFlagResponse])
async def list_feature_flags(
    scope: str | None = None,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> list[FeatureFlagResponse]:
    return await service.list_feature_flags(scope)


@router.get("/feature-flags/{key}", response_model=FeatureFlagResponse)
async def get_feature_flag(
    key: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> FeatureFlagResponse:
    return await service.get_feature_flag(key)


@router.post("/feature-flags", response_model=FeatureFlagResponse, status_code=201)
async def create_feature_flag(
    body: dict,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> FeatureFlagResponse:
    return await service.create_feature_flag(
        body["key"],
        body["name"],
        description=body.get("description", ""),
        flag_type=body.get("flag_type", "boolean"),
        scope=body.get("scope", "global"),
        enabled=body.get("enabled", False),
        percentage=body.get("percentage", 100.0),
    )


@router.patch("/feature-flags/{key}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    key: str,
    body: dict,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> FeatureFlagResponse:
    return await service.update_feature_flag(key, **body)


@router.delete("/feature-flags/{key}", response_model=MessageResponse)
async def delete_feature_flag(
    key: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> MessageResponse:
    return await service.delete_feature_flag(key)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
@router.get("/admin/overview", response_model=PlatformOverviewResponse)
async def get_platform_overview(
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> PlatformOverviewResponse:
    return await service.get_platform_overview()


@router.get("/admin/health")
async def get_system_health(
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> dict:
    return await service.get_system_health()


@router.get("/admin/providers")
async def get_provider_health(
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> dict:
    return await service.get_provider_health()


@router.get("/admin/audit-logs")
async def get_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> list[dict]:
    return await service.get_recent_audit_logs(limit=limit)


@router.get("/admin/billing")
async def get_billing_overview(
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> dict:
    return await service.get_billing_overview()


@router.get("/admin/usage")
async def get_usage_dashboard(
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> dict:
    return await service.get_usage_dashboard()


@router.post("/admin/users/{user_id}/suspend", response_model=MessageResponse)
async def suspend_user(
    user_id: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> MessageResponse:
    return await service.suspend_user(user_id)


@router.post("/admin/users/{user_id}/activate", response_model=MessageResponse)
async def activate_user(
    user_id: str,
    user: dict = Depends(require_authentication),
    service: PlatformService = Depends(_get_platform_service),
) -> MessageResponse:
    return await service.activate_user(user_id)
