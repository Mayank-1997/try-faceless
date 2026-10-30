"""Tests for the Metrics Collector."""

from __future__ import annotations

from src.core.enums import AgentType


class TestMetricsCollector:
    def _make_config(self):
        from tests.factories import make_test_config_service
        return make_test_config_service()

    def test_record_execution(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        collector.record_execution(
            AgentType.DIRECTOR,
            success=True,
            execution_time_ms=500,
            cost_usd=0.05,
            tokens=1000,
        )
        metrics = collector.get_agent_metrics(AgentType.DIRECTOR)
        assert metrics.execution_count == 1
        assert metrics.success_count == 1
        assert metrics.average_execution_time_ms == 500.0
        assert metrics.average_cost_usd == 0.05
        assert metrics.average_tokens == 1000.0

    def test_failure_tracking(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        collector.record_execution(AgentType.DIRECTOR, success=False, execution_time_ms=200)
        metrics = collector.get_agent_metrics(AgentType.DIRECTOR)
        assert metrics.failure_count == 1
        assert metrics.success_count == 0
        assert metrics.success_rate == 0.0

    def test_success_rate(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        for i in range(8):
            collector.record_execution(AgentType.DIRECTOR, success=True, execution_time_ms=100)
        for i in range(2):
            collector.record_execution(AgentType.DIRECTOR, success=False, execution_time_ms=100)
        metrics = collector.get_agent_metrics(AgentType.DIRECTOR)
        assert metrics.execution_count == 10
        assert metrics.success_rate == 0.8

    def test_retry_tracking(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        collector.record_execution(
            AgentType.DIRECTOR, success=True, execution_time_ms=500, retries=2
        )
        metrics = collector.get_agent_metrics(AgentType.DIRECTOR)
        assert metrics.retry_count == 2

    def test_generation_success_rate_across_agents(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        collector.record_execution(AgentType.DIRECTOR, success=True, execution_time_ms=100)
        collector.record_execution(AgentType.SCENE_PLANNER, success=True, execution_time_ms=200)
        collector.record_execution(AgentType.SCENE_PLANNER, success=False, execution_time_ms=50)
        assert collector.get_generation_success_rate() == (2 / 3)

    def test_average_cost(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        collector.record_execution(AgentType.DIRECTOR, success=True, execution_time_ms=100, cost_usd=0.05)
        collector.record_execution(AgentType.DIRECTOR, success=True, execution_time_ms=100, cost_usd=0.15)
        assert collector.get_average_cost() == 0.1

    def test_average_tokens(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        collector.record_execution(AgentType.DIRECTOR, success=True, execution_time_ms=100, tokens=500)
        collector.record_execution(AgentType.DIRECTOR, success=True, execution_time_ms=100, tokens=1500)
        assert collector.get_average_tokens() == 1000.0

    def test_error_summary(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        collector.record_error("AIProviderError", AgentType.DIRECTOR)
        collector.record_error("AIProviderError", AgentType.DIRECTOR)
        collector.record_error("TimeoutError")
        errors = collector.get_error_summary()
        assert errors["director:AIProviderError"] == 2
        assert errors["TimeoutError"] == 1

    def test_operation_timing(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        collector.record_timing("render", 5000)
        collector.record_timing("render", 3000)
        assert collector.get_operation_average_time("render") == 4000.0

    def test_custom_metric_point(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        collector.record_point("queue_depth", 42.0, tags={"queue": "render"}, unit="count")
        points = collector.get_recent_points(name="queue_depth")
        assert len(points) == 1
        assert points[0].value == 42.0

    def test_get_summary(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        collector.record_execution(AgentType.DIRECTOR, success=True, execution_time_ms=500, cost_usd=0.05, tokens=1000)
        summary = collector.get_summary()
        assert summary["total_executions"] == 1
        assert summary["total_successes"] == 1
        assert summary["generation_success_rate"] == 1.0
        assert "agent_metrics" in summary

    def test_clear(self):
        from src.infrastructure.observability.metrics import MetricsCollector

        collector = MetricsCollector(self._make_config())
        collector.record_execution(AgentType.DIRECTOR, success=True, execution_time_ms=100)
        collector.clear()
        metrics = collector.get_agent_metrics(AgentType.DIRECTOR)
        assert metrics.execution_count == 0
