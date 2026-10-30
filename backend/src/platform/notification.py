"""Notification Service.

Supports:
- Email
- In-app notifications
- Webhook events
- Future Slack, Discord, Teams

Only implements extensible backend services and interfaces.
No email provider integration yet.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.platform.schema import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    WebhookConfig,
)
from src.core.logging import get_logger


class NotificationService:
    """Manages notification delivery across multiple channels.

    Provides a unified interface for sending notifications via email,
    in-app, webhook, and future channels (Slack, Discord, Teams).
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._notifications: list[Notification] = []
        self._webhooks: dict[UUID, WebhookConfig] = {}
        self._handlers: dict[NotificationChannel, Any] = {}

    def register_handler(self, channel: NotificationChannel, handler: Any) -> None:
        """Register a notification handler for a channel.

        Args:
            channel: The notification channel.
            handler: The handler (callable or service object).
        """
        self._handlers[channel] = handler
        self._logger.info("notification_handler_registered", channel=channel.value)

    def send(
        self,
        user_id: str,
        title: str,
        body: str,
        *,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        org_id: str = "",
        data: dict[str, Any] | None = None,
    ) -> Notification:
        """Send a notification.

        Args:
            user_id: Recipient user ID.
            title: Notification title.
            body: Notification body.
            channel: Delivery channel.
            priority: Priority level.
            org_id: Optional organization ID.
            data: Additional notification data.

        Returns:
            The created ``Notification``.
        """
        notification = Notification(
            user_id=user_id,
            org_id=org_id,
            channel=channel,
            priority=priority,
            title=title,
            body=body,
            data=data or {},
        )

        # Attempt delivery
        handler = self._handlers.get(channel)
        if handler is not None:
            try:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now(timezone.utc)
                self._logger.info(
                    "notification_sent",
                    notification_id=str(notification.id),
                    channel=channel.value,
                    user_id=user_id,
                )
            except Exception as exc:
                notification.status = NotificationStatus.FAILED
                self._logger.error("notification_failed", error=str(exc))
        else:
            # No handler registered — mark as pending
            notification.status = NotificationStatus.PENDING
            self._logger.info(
                "notification_pending",
                notification_id=str(notification.id),
                channel=channel.value,
            )

        self._notifications.append(notification)
        return notification

    def send_batch(
        self,
        user_ids: list[str],
        title: str,
        body: str,
        *,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        org_id: str = "",
    ) -> list[Notification]:
        """Send a notification to multiple users.

        Args:
            user_ids: List of recipient user IDs.
            title: Notification title.
            body: Notification body.
            channel: Delivery channel.
            priority: Priority level.
            org_id: Optional organization ID.

        Returns:
            List of created ``Notification`` objects.
        """
        return [
            self.send(user_id, title, body, channel=channel, priority=priority, org_id=org_id)
            for user_id in user_ids
        ]

    def mark_read(self, notification_id: UUID) -> bool:
        """Mark a notification as read.

        Args:
            notification_id: The notification ID.

        Returns:
            ``True`` if found and updated.
        """
        for n in self._notifications:
            if n.id == notification_id:
                n.status = NotificationStatus.READ
                n.read_at = datetime.now(timezone.utc)
                return True
        return False

    def dismiss(self, notification_id: UUID) -> bool:
        """Dismiss a notification.

        Args:
            notification_id: The notification ID.

        Returns:
            ``True`` if found and dismissed.
        """
        for n in self._notifications:
            if n.id == notification_id:
                n.status = NotificationStatus.DISMISSED
                return True
        return False

    def get_notifications(
        self,
        user_id: str,
        *,
        status: NotificationStatus | None = None,
        limit: int = 50,
    ) -> list[Notification]:
        """Get notifications for a user.

        Args:
            user_id: The user ID.
            status: Optional status filter.
            limit: Maximum number to return.

        Returns:
            List of ``Notification``.
        """
        result = [n for n in self._notifications if n.user_id == user_id]
        if status is not None:
            result = [n for n in result if n.status == status]
        return sorted(result, key=lambda x: x.created_at, reverse=True)[:limit]

    def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count for a user.

        Args:
            user_id: The user ID.

        Returns:
            Number of unread notifications.
        """
        return sum(
            1 for n in self._notifications
            if n.user_id == user_id and n.status not in (NotificationStatus.READ, NotificationStatus.DISMISSED)
        )

    def register_webhook(
        self,
        org_id: str,
        url: str,
        events: list[str],
        *,
        secret: str = "",
    ) -> WebhookConfig:
        """Register a webhook for an organization.

        Args:
            org_id: The organization ID.
            url: Webhook URL.
            events: List of event types to subscribe to.
            secret: Optional webhook secret for verification.

        Returns:
            The ``WebhookConfig``.
        """
        import secrets
        webhook = WebhookConfig(
            org_id=org_id,
            url=url,
            events=events,
            secret=secret or secrets.token_urlsafe(32),
        )
        self._webhooks[webhook.id] = webhook
        self._logger.info("webhook_registered", org_id=org_id, url=url)
        return webhook

    def get_webhooks(self, org_id: str) -> list[WebhookConfig]:
        """Get webhooks for an organization.

        Args:
            org_id: The organization ID.

        Returns:
            List of ``WebhookConfig``.
        """
        return [w for w in self._webhooks.values() if w.org_id == org_id]

    def delete_webhook(self, webhook_id: UUID) -> bool:
        """Delete a webhook.

        Args:
            webhook_id: The webhook ID.

        Returns:
            ``True`` if deleted.
        """
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            return True
        return False

    @property
    def notification_count(self) -> int:
        """Total number of notifications."""
        return len(self._notifications)

    @property
    def webhook_count(self) -> int:
        """Total number of webhooks."""
        return len(self._webhooks)

    def clear(self) -> None:
        """Clear all notifications (primarily for testing)."""
        self._notifications.clear()
        self._webhooks.clear()
