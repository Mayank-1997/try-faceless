"""Tests for the Event Bus."""

from __future__ import annotations

import asyncio
import pytest

from src.application.services.event_bus import Event, EventBus
from src.core.exceptions import EventPublishError


class TestEventBus:
    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.mark.asyncio
    async def test_initialize(self, bus):
        await bus.initialize()
        assert bus._initialized is True

    @pytest.mark.asyncio
    async def test_publish_not_initialized_raises(self, bus):
        event = Event(event_type="TestEvent", data={})
        with pytest.raises(EventPublishError):
            await bus.publish(event)

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, bus):
        await bus.initialize()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe("TestEvent", handler)
        event = Event(event_type="TestEvent", data={"key": "value"})
        await bus.publish(event)

        assert len(received) == 1
        assert received[0].data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, bus):
        await bus.initialize()
        results1: list[Event] = []
        results2: list[Event] = []

        async def handler1(event: Event) -> None:
            results1.append(event)

        async def handler2(event: Event) -> None:
            results2.append(event)

        bus.subscribe("TestEvent", handler1)
        bus.subscribe("TestEvent", handler2)

        await bus.publish(Event(event_type="TestEvent", data={"n": 1}))

        assert len(results1) == 1
        assert len(results2) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        await bus.initialize()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe("TestEvent", handler)
        bus.unsubscribe("TestEvent", handler)

        await bus.publish(Event(event_type="TestEvent", data={}))
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_no_subscribers(self, bus):
        await bus.initialize()
        # Should not raise
        await bus.publish(Event(event_type="NoSubscribers", data={}))

    @pytest.mark.asyncio
    async def test_subscriber_error_does_not_block_others(self, bus):
        await bus.initialize()
        received: list[Event] = []

        async def failing_handler(event: Event) -> None:
            raise ValueError("Handler error")

        async def good_handler(event: Event) -> None:
            received.append(event)

        bus.subscribe("TestEvent", failing_handler)
        bus.subscribe("TestEvent", good_handler)

        await bus.publish(Event(event_type="TestEvent", data={}))
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_event_history(self, bus):
        await bus.initialize()
        await bus.publish(Event(event_type="EventA", data={"n": 1}))
        await bus.publish(Event(event_type="EventB", data={"n": 2}))
        await bus.publish(Event(event_type="EventA", data={"n": 3}))

        history = bus.get_history()
        assert len(history) == 3

        history_a = bus.get_history(event_type="EventA")
        assert len(history_a) == 2

    @pytest.mark.asyncio
    async def test_subscriber_count(self, bus):
        await bus.initialize()

        async def handler1(event: Event) -> None:
            pass

        async def handler2(event: Event) -> None:
            pass

        bus.subscribe("TestEvent", handler1)
        bus.subscribe("TestEvent", handler2)
        assert bus.get_subscriber_count("TestEvent") == 2

    @pytest.mark.asyncio
    async def test_shutdown(self, bus):
        await bus.initialize()
        await bus.shutdown()
        assert bus._initialized is False


class TestEvent:
    def test_creation(self):
        event = Event(
            event_type="TestEvent",
            data={"key": "value"},
            source="test_module",
        )
        assert event.event_type == "TestEvent"
        assert event.data == {"key": "value"}
        assert event.source == "test_module"
        assert event.timestamp is not None

    def test_defaults(self):
        event = Event(event_type="TestEvent")
        assert event.data == {}
        assert event.correlation_id is None
