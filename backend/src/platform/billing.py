"""Billing Service.

Supports:
- Free, Pro, Enterprise plans
- Usage-based billing
- Credits
- Subscriptions
- Invoices
- Future Stripe integration (interface only)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from src.platform.schema import (
    CreditBalance,
    CreditType,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Plan,
    PlanFeatures,
    PlanType,
    Subscription,
    SubscriptionStatus,
)
from src.core.logging import get_logger


class BillingService:
    """Billing service for plan management, credits, and invoices.

    Provides extensible backend services and interfaces for billing.
    Stripe integration is deferred to a future phase.
    """

    # Default plans
    DEFAULT_PLANS: dict[str, Plan] = {
        "free": Plan(
            id="free",
            name="Free",
            plan_type=PlanType.FREE,
            price_monthly=0.0,
            price_yearly=0.0,
            features=PlanFeatures(
                max_projects=5,
                max_images_per_month=100,
                max_videos_per_month=10,
                max_voice_minutes_per_month=30,
                max_rendering_minutes_per_month=60,
                max_storage_gb=5,
                max_bandwidth_gb=50,
                max_team_members=3,
            ),
            description="Free plan for getting started",
        ),
        "pro": Plan(
            id="pro",
            name="Pro",
            plan_type=PlanType.PRO,
            price_monthly=29.99,
            price_yearly=299.99,
            features=PlanFeatures(
                max_projects=50,
                max_images_per_month=1000,
                max_videos_per_month=100,
                max_voice_minutes_per_month=300,
                max_rendering_minutes_per_month=600,
                max_storage_gb=100,
                max_bandwidth_gb=500,
                max_team_members=10,
                custom_branding=True,
                priority_support=True,
                api_access=True,
                advanced_analytics=True,
            ),
            description="Professional plan for creators",
        ),
        "enterprise": Plan(
            id="enterprise",
            name="Enterprise",
            plan_type=PlanType.ENTERPRISE,
            price_monthly=299.99,
            price_yearly=2999.99,
            features=PlanFeatures(
                max_projects=999999,
                max_images_per_month=999999,
                max_videos_per_month=999999,
                max_voice_minutes_per_month=999999,
                max_rendering_minutes_per_month=999999,
                max_storage_gb=999999,
                max_bandwidth_gb=999999,
                max_team_members=999999,
                custom_branding=True,
                priority_support=True,
                api_access=True,
                advanced_analytics=True,
                white_label=True,
                sso=True,
            ),
            description="Enterprise plan for large organizations",
        ),
    }

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._plans: dict[str, Plan] = dict(self.DEFAULT_PLANS)
        self._subscriptions: dict[str, Subscription] = {}  # user_id -> subscription
        self._credit_balances: dict[str, CreditBalance] = {}  # user_id -> balance
        self._invoices: list[Invoice] = []

    def get_plan(self, plan_id: str) -> Plan | None:
        """Get a plan by ID.

        Args:
            plan_id: The plan ID.

        Returns:
            The ``Plan`` if found, ``None`` otherwise.
        """
        return self._plans.get(plan_id)

    def list_plans(self) -> list[Plan]:
        """List all available plans."""
        return list(self._plans.values())

    def create_plan(self, plan: Plan) -> Plan:
        """Create a custom plan.

        Args:
            plan: The plan to create.

        Returns:
            The created plan.
        """
        self._plans[plan.id] = plan
        self._logger.info("plan_created", plan_id=plan.id, name=plan.name)
        return plan

    def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        *,
        org_id: str = "",
        trial_days: int = 0,
    ) -> Subscription:
        """Create a subscription for a user.

        Args:
            user_id: The user ID.
            plan_id: The plan ID.
            org_id: Optional organization ID.
            trial_days: Optional trial period in days.

        Returns:
            The created ``Subscription``.

        Raises:
            ValueError: If the plan doesn't exist.
        """
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan '{plan_id}' not found")

        now = datetime.now(timezone.utc)
        status = SubscriptionStatus.ACTIVE
        trial_end: datetime | None = None

        if trial_days > 0:
            status = SubscriptionStatus.TRIALING
            trial_end = now + timedelta(days=trial_days)

        subscription = Subscription(
            user_id=user_id,
            org_id=org_id,
            plan_id=plan_id,
            plan_type=plan.plan_type,
            status=status,
            started_at=now,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            trial_end=trial_end,
        )

        self._subscriptions[user_id] = subscription
        self._logger.info(
            "subscription_created",
            user_id=user_id,
            plan_id=plan_id,
            status=status.value,
        )
        return subscription

    def get_subscription(self, user_id: str) -> Subscription | None:
        """Get a user's subscription.

        Args:
            user_id: The user ID.

        Returns:
            The ``Subscription`` if found, ``None`` otherwise.
        """
        return self._subscriptions.get(user_id)

    def cancel_subscription(self, user_id: str) -> Subscription | None:
        """Cancel a user's subscription.

        Args:
            user_id: The user ID.

        Returns:
            The cancelled ``Subscription`` if found, ``None`` otherwise.
        """
        sub = self._subscriptions.get(user_id)
        if sub is None:
            return None
        sub.status = SubscriptionStatus.CANCELLED
        sub.cancelled_at = datetime.now(timezone.utc)
        self._logger.info("subscription_cancelled", user_id=user_id)
        return sub

    def change_plan(self, user_id: str, new_plan_id: str) -> Subscription:
        """Change a user's plan.

        Args:
            user_id: The user ID.
            new_plan_id: The new plan ID.

        Returns:
            The updated ``Subscription``.

        Raises:
            ValueError: If subscription or plan doesn't exist.
        """
        sub = self._subscriptions.get(user_id)
        if sub is None:
            raise ValueError(f"No subscription found for user '{user_id}'")

        plan = self.get_plan(new_plan_id)
        if plan is None:
            raise ValueError(f"Plan '{new_plan_id}' not found")

        sub.plan_id = new_plan_id
        sub.plan_type = plan.plan_type
        self._logger.info("plan_changed", user_id=user_id, new_plan=new_plan_id)
        return sub

    def get_credit_balance(self, user_id: str) -> CreditBalance:
        """Get credit balance for a user.

        Args:
            user_id: The user ID.

        Returns:
            The user's ``CreditBalance``.
        """
        if user_id not in self._credit_balances:
            self._credit_balances[user_id] = CreditBalance(user_id=user_id)
        return self._credit_balances[user_id]

    def add_credits(self, user_id: str, credit_type: str, amount: float) -> float:
        """Add credits to a user's balance.

        Args:
            user_id: The user ID.
            credit_type: The credit type.
            amount: The amount to add.

        Returns:
            The new balance.
        """
        balance = self.get_credit_balance(user_id)
        new_balance = balance.add_credits(credit_type, amount)
        self._logger.info("credits_added", user_id=user_id, credit_type=credit_type, amount=amount)
        return new_balance

    def consume_credits(self, user_id: str, credit_type: str, amount: float) -> bool:
        """Consume credits from a user's balance.

        Args:
            user_id: The user ID.
            credit_type: The credit type.
            amount: The amount to consume.

        Returns:
            ``True`` if credits were consumed, ``False`` if insufficient.
        """
        balance = self.get_credit_balance(user_id)
        success = balance.consume_credits(credit_type, amount)
        if success:
            self._logger.info("credits_consumed", user_id=user_id, credit_type=credit_type, amount=amount)
        else:
            self._logger.warning("credits_insufficient", user_id=user_id, credit_type=credit_type, amount=amount)
        return success

    def create_invoice(
        self,
        user_id: str,
        items: list[InvoiceItem],
        *,
        org_id: str = "",
        subscription_id: UUID | None = None,
    ) -> Invoice:
        """Create an invoice.

        Args:
            user_id: The user ID.
            items: Invoice line items.
            org_id: Optional organization ID.
            subscription_id: Optional subscription ID.

        Returns:
            The created ``Invoice``.
        """
        invoice = Invoice(
            user_id=user_id,
            org_id=org_id,
            subscription_id=subscription_id,
            items=items,
            status=InvoiceStatus.PENDING,
            due_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        invoice.calculate_totals()
        self._invoices.append(invoice)
        self._logger.info("invoice_created", invoice_id=str(invoice.id), total=invoice.total)
        return invoice

    def pay_invoice(self, invoice_id: UUID) -> Invoice | None:
        """Mark an invoice as paid.

        Args:
            invoice_id: The invoice ID.

        Returns:
            The paid ``Invoice`` if found, ``None`` otherwise.
        """
        for inv in self._invoices:
            if inv.id == invoice_id:
                inv.status = InvoiceStatus.PAID
                inv.paid_at = datetime.now(timezone.utc)
                self._logger.info("invoice_paid", invoice_id=str(invoice_id))
                return inv
        return None

    def get_invoices(self, user_id: str | None = None) -> list[Invoice]:
        """Get invoices, optionally filtered by user.

        Args:
            user_id: Optional user ID filter.

        Returns:
            List of invoices.
        """
        if user_id:
            return [inv for inv in self._invoices if inv.user_id == user_id]
        return list(self._invoices)

    def check_plan_limits(self, user_id: str, resource: str, current_usage: float) -> bool:
        """Check if usage is within plan limits.

        Args:
            user_id: The user ID.
            resource: Resource type (e.g. "images", "videos").
            current_usage: Current usage amount.

        Returns:
            ``True`` if within limits.
        """
        sub = self.get_subscription(user_id)
        if sub is None:
            plan = self.get_plan("free")
        else:
            plan = self.get_plan(sub.plan_id)
        if plan is None:
            return True

        limits = {
            "images": plan.features.max_images_per_month,
            "videos": plan.features.max_videos_per_month,
            "voice_minutes": plan.features.max_voice_minutes_per_month,
            "rendering_minutes": plan.features.max_rendering_minutes_per_month,
            "storage_gb": plan.features.max_storage_gb,
            "projects": plan.features.max_projects,
        }

        limit = limits.get(resource, 0)
        if limit <= 0:
            return True
        return current_usage < limit
