"""Tests for the Token Tracker."""

from __future__ import annotations

from src.application.services.token_tracker import TokenEntry, TokenTracker
from src.core.enums import AIProvider, AgentType


class TestTokenTracker:
    def test_record_and_get_project_tokens(self):
        tracker = TokenTracker()
        entry = TokenEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            input_tokens=500,
            output_tokens=200,
            project_id="proj-1",
        )
        tracker.record(entry)
        assert tracker.get_project_tokens("proj-1") == 700

    def test_multiple_entries_accumulate(self):
        tracker = TokenTracker()
        for i in range(3):
            tracker.record(TokenEntry(
                agent_type=AgentType.DIRECTOR,
                provider=AIProvider.GEMINI,
                model="gemini-2.5-pro",
                input_tokens=100,
                output_tokens=50,
                project_id="proj-1",
            ))
        assert tracker.get_project_tokens("proj-1") == 450

    def test_get_agent_tokens(self):
        tracker = TokenTracker()
        tracker.record(TokenEntry(
            agent_type=AgentType.SCENE_PLANNER,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            input_tokens=300,
            output_tokens=100,
        ))
        assert tracker.get_agent_tokens(AgentType.SCENE_PLANNER) == 400

    def test_get_provider_tokens(self):
        tracker = TokenTracker()
        tracker.record(TokenEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            input_tokens=200,
            output_tokens=100,
        ))
        assert tracker.get_provider_tokens(AIProvider.GEMINI) == 300

    def test_cached_tokens(self):
        tracker = TokenTracker()
        entry = TokenEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            input_tokens=100,
            output_tokens=50,
            cached_tokens=200,
            project_id="proj-1",
        )
        tracker.record(entry)
        summary = tracker.get_project_summary("proj-1")
        assert summary.total_cached_tokens == 200
        assert summary.total_tokens == 350

    def test_get_project_summary(self):
        tracker = TokenTracker()
        tracker.record(TokenEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            input_tokens=500,
            output_tokens=200,
            project_id="proj-1",
        ))
        tracker.record(TokenEntry(
            agent_type=AgentType.SCENE_PLANNER,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-flash",
            input_tokens=300,
            output_tokens=100,
            project_id="proj-1",
        ))
        summary = tracker.get_project_summary("proj-1")
        assert summary.total_input_tokens == 800
        assert summary.total_output_tokens == 300
        assert summary.total_tokens == 1100
        assert summary.entry_count == 2
        assert "director" in summary.by_agent

    def test_clear(self):
        tracker = TokenTracker()
        tracker.record(TokenEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            input_tokens=100,
            project_id="proj-1",
        ))
        tracker.clear()
        assert tracker.get_project_tokens("proj-1") == 0
        assert len(tracker.get_all_entries()) == 0

    def test_token_entry_total_property(self):
        entry = TokenEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            input_tokens=100,
            output_tokens=50,
            cached_tokens=25,
        )
        assert entry.total_tokens == 175

    def test_get_user_tokens(self):
        tracker = TokenTracker()
        tracker.record(TokenEntry(
            agent_type=AgentType.DIRECTOR,
            provider=AIProvider.GEMINI,
            model="gemini-2.5-pro",
            input_tokens=500,
            output_tokens=200,
            user_id="user-1",
        ))
        assert tracker.get_user_tokens("user-1") == 700
