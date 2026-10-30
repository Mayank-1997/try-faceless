"""Tests for the Cost Tracker."""

from __future__ import annotations

from src.application.services.cost_tracker import CostEntry, CostTracker
from src.core.enums import AIProvider, AgentType


class TestCostTracker:
    def test_record_and_get_project_cost(self):
        tracker = CostTracker(config=None)
        entry = CostEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            cost_usd=0.05,
            project_id="proj-1",
        )
        tracker.record(entry)
        assert tracker.get_project_cost("proj-1") == 0.05

    def test_multiple_entries_accumulate(self):
        tracker = CostTracker(config=None)
        for i in range(5):
            tracker.record(CostEntry(
                agent_type=AgentType.DIRECTOR,
                provider=AIProvider.GEMINI,
                model="gemini-2.5-pro",
                cost_usd=0.01 * (i + 1),
                project_id="proj-1",
            ))
        assert tracker.get_project_cost("proj-1") == 0.15

    def test_get_agent_cost(self):
        tracker = CostTracker(config=None)
        tracker.record(CostEntry(
            agent_type=AgentType.SCENE_PLANNER,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            cost_usd=0.03,
        ))
        tracker.record(CostEntry(
            agent_type=AgentType.SCENE_PLANNER,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            cost_usd=0.02,
        ))
        assert tracker.get_agent_cost(AgentType.SCENE_PLANNER) == 0.05

    def test_get_provider_cost(self):
        tracker = CostTracker(config=None)
        tracker.record(CostEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            cost_usd=0.04,
        ))
        tracker.record(CostEntry(
            agent_type=AgentType.SCENE_PLANNER,
            provider=AIProvider.IMAGEN,
            model="imagen-3",
            cost_usd=0.08,
        ))
        assert tracker.get_provider_cost(AIProvider.GEMINI) == 0.04
        assert tracker.get_provider_cost(AIProvider.IMAGEN) == 0.08

    def test_get_project_summary(self):
        tracker = CostTracker(config=None)
        tracker.record(CostEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            cost_usd=0.05,
            project_id="proj-1",
        ))
        tracker.record(CostEntry(
            agent_type=AgentType.SCENE_PLANNER,
            provider=AIProvider.IMAGEN,
            model="imagen-3",
            cost_usd=0.04,
            project_id="proj-1",
        ))
        summary = tracker.get_project_summary("proj-1")
        assert summary.total_cost_usd == 0.09
        assert summary.llm_cost_usd == 0.05
        assert summary.image_cost_usd == 0.04
        assert summary.entry_count == 2
        assert "director" in summary.by_agent
        assert "gemini" in summary.by_provider

    def test_clear(self):
        tracker = CostTracker(config=None)
        tracker.record(CostEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            cost_usd=0.05,
            project_id="proj-1",
        ))
        tracker.clear()
        assert tracker.get_project_cost("proj-1") == 0.0
        assert len(tracker.get_all_entries()) == 0

    def test_get_user_cost(self):
        tracker = CostTracker(config=None)
        tracker.record(CostEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            cost_usd=0.05,
            user_id="user-1",
        ))
        assert tracker.get_user_cost("user-1") == 0.05
