"""Event Bus — async pub/sub for loose coupling between components.

The event bus allows components to communicate without direct references
to each other.  Publishers emit events; subscribers react independently.

Example events:
- ``ResearchCompleted``
- ``ScriptCompleted``
- ``SceneGenerated``
- ``AssetCreated``
- ``RenderCompleted``
- ``PublishCompleted``
- ``CostUpdated``

Usage::

    bus = EventBus()
    await bus.initialize()

    # Subscribe
    bus.subscribe("ResearchCompleted", handle_research)

    # Publish
    await bus.publish(Event(
        event_type="ResearchCompleted",
        data={"project_id": "...", "summary": "..."},
    ))
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field

from src.core.exceptions import EventPublishError
from src.core.logging import get_logger


# Type alias for event handler functions
EventHandler = Callable[["Event"], Awaitable[None]]


class Event(BaseModel):
    """A single event emitted on the event bus.

    Attributes:
        event_type: The event type identifier (e.g. "ResearchCompleted").
        data: Arbitrary structured data payload.
        timestamp: When the event was created.
        correlation_id: Optional correlation ID for tracing.
        source: The component that emitted the event.
    """

    event_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = None
    source: str | None = None


class EventBus:
    """Async event bus for pub/sub communication.

    Events are delivered to all subscribers asynchronously.  Subscriber
    errors are caught and logged — they do not block other subscribers
    or the publisher.
    """

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._initialized = False
        self._event_history: list[Event] = []

    async def initialize(self) -> None:
        """Initialise the event bus."""
        self._initialized = True
        self._logger.info("event_bus_initialized")

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event type.

        Args:
            event_type: The event type to subscribe to.
            handler: An async callable that receives an ``Event``.
        """
        self._subscribers[event_type].append(handler)
        self._logger.info(
            "event_subscribed",
            event_type=event_type,
            handler=handler.__name__ if hasattr(handler, "__name__") else str(handler),
        )

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type.

        Args:
            event_type: The event type to unsubscribe from.
            handler: The handler to remove.
        """
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]
            self._logger.info(
                "event_unsubscribed",
                event_type=event_type,
                handler=handler.__name__ if hasattr(handler, "__name__") else str(handler),
            )

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers.

        Subscribers are notified concurrently.  Errors in individual
        subscribers are caught and logged.

        Args:
            event: The event to publish.

        Raises:
            EventPublishError: If the bus is not initialised.
        """
        if not self._initialized:
            raise EventPublishError(event.event_type, "Event bus is not initialised")

        self._event_history.append(event)
        handlers = self._subscribers.get(event.event_type, [])

        if not handlers:
            self._logger.debug(
                "event_no_subscribers",
                event_type=event.event_type,
            )
            return

        self._logger.info(
            "event_published",
            event_type=event.event_type,
            subscriber_count=len(handlers),
            correlation_id=event.correlation_id,
        )

        # Notify all subscribers concurrently
        results = await asyncio.gather(
            *[self._safe_notify(handler, event) for handler in handlers],
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                self._logger.error(
                    "event_subscriber_error",
                    event_type=event.event_type,
                    error=str(result),
                )

    async def _safe_notify(self, handler: EventHandler, event: Event) -> None:
        """Call a subscriber handler with error handling."""
        try:
            await handler(event)
        except Exception as exc:
            self._logger.error(
                "event_handler_error",
                event_type=event.event_type,
                handler=handler.__name__ if hasattr(handler, "__name__") else str(handler),
                error=str(exc),
            )

    def get_history(self, event_type: str | None = None, limit: int = 100) -> list[Event]:
        """Get recent event history.

        Args:
            event_type: Optional filter by event type.
            limit: Maximum number of events to return.

        Returns:
            List of recent events, newest first.
        """
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return list(reversed(events[-limit:]))

    def get_subscriber_count(self, event_type: str) -> int:
        """Get the number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, []))

    async def shutdown(self) -> None:
        """Release resources."""
        self._subscribers.clear()
        self._event_history.clear()
        self._initialized = False
        self._logger.info("event_bus_shutdown")
