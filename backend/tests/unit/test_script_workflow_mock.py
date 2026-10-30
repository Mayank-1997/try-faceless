"""Mocked tests for the script workflow from outline to review.

Uses a fake prompt executor so no real Gemini calls are made.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from src.ai.agents.response import AIResponse
from src.ai.agents.script.schema import NarrativeStrategy, OutlineSection, ScriptOutline
from src.ai.agents.script.script_review import ScriptReviewAgent
from src.ai.agents.script.section_writer import SectionWriterAgent
from src.ai.agents.script.transition import TransitionAgent
from src.workflow.contexts import NodeContext
from src.workflow.state import ProjectInfo, ResearchData, ScriptData, TopicData, WorkflowState


def _ai_response(structured_data: dict | None = None) -> AIResponse:
    return AIResponse(
        success=True,
        response=json.dumps(structured_data),
        structured_data=structured_data,
        timestamp=datetime.now(UTC),
    )


def _build_state() -> WorkflowState:
    narrative_strategy = NarrativeStrategy.model_validate({
        "style": "storytelling",
        "rationale": "Immersive storytelling",
        "flow": "Start crash, learn, explore, rescue",
        "pacing": "varied",
        "tone": "dramatic",
        "emotional_arc": "terror to triumph",
        "key_beats": ["crash", "survival", "fauna", "ruins", "rescue"],
        "audience_alignment": "Thrill-seeking escapist",
    })

    script_outline = ScriptOutline(
        title="A Boy Survived Alone on a Mysterious Island",
        opening="",
        closing="",
        sections=[
            OutlineSection(
                section_id="s1",
                title="The Crash",
                description="Leo wakes up alone on an alien beach after a plane crash.",
                key_talking_points=["violent crash", "silence", "jungle"],
                estimated_time_seconds=45,
                target_word_count=112,
            ),
            OutlineSection(
                section_id="s2",
                title="Primal Ingenuity",
                description="Leo builds shelter, distills water, and makes fire.",
                key_talking_points=["airplane seat frame", "solar still", "bow drill"],
                estimated_time_seconds=50,
                target_word_count=125,
            ),
        ],
    )

    return WorkflowState(
        project=ProjectInfo(),
        topic=TopicData(
            raw_topic="A Boy Survived Alone on a Mysterious Island",
            expanded_topic="A Boy Survived Alone on a Mysterious Island",
        ),
        research=ResearchData(
            metadata={
                "research_package": {
                    "topic_analysis": {
                        "expanded_topic": "A Boy Survived Alone on a Mysterious Island",
                        "target_duration_seconds": 300,
                        "target_audience": "Thrill-Seeking Escapist",
                    },
                    "audience": {
                        "primary_persona": {
                            "persona_name": "Thrill-Seeking Escapist",
                        }
                    },
                    "fact_verification": {
                        "verified_facts": [
                            {"category": "survival", "fact": "Bow-drill fires take hours."}
                        ]
                    },
                }
            }
        ),
        script=ScriptData(
            metadata={
                "narrative_strategy": narrative_strategy.model_dump(),
                "script_outline": script_outline.model_dump(),
            }
        ),
    )


class FakePromptExecutor:
    """Fake prompt executor that returns different canned responses for each agent."""

    async def execute_template(self, template, variables, *, agent_name: str = "", options=None):
        if agent_name == "section_writer":
            return _ai_response({
                "sections": [
                    {
                        "section_id": "s1",
                        "title": "The Crash",
                        "narration": "The sky didn't just break; it shattered in a deafening roar.",
                        "estimated_duration_seconds": 45,
                        "word_count": 100,
                        "emotion": "dramatic",
                        "importance": "high",
                        "purpose": "entertain",
                        "references": [],
                        "facts_used": ["Bow-drill fires take hours."],
                        "examples": [],
                        "future_scene_count": 3,
                    },
                    {
                        "section_id": "s2",
                        "title": "Primal Ingenuity",
                        "narration": (
                            "Surviving the first week required "
                            "turning raw terror into mechanics."
                        ),
                        "estimated_duration_seconds": 50,
                        "word_count": 110,
                        "emotion": "curious",
                        "importance": "high",
                        "purpose": "inform",
                        "references": [],
                        "facts_used": [],
                        "examples": [],
                        "future_scene_count": 3,
                    },
                ]
            })

        if agent_name == "transition":
            return _ai_response({
                "transitions": {
                    "s1": "But surviving the crash was only the beginning of Leo's trial.",
                    "s2": "With basic survival secured, the island's deeper mystery began to call.",
                },
                "flow_analysis": "Strong escalation from catastrophe to resourcefulness.",
                "smoothness_score": 0.9,
            })

        if agent_name == "script_review":
            return _ai_response({
                "logic_score": 0.9,
                "flow_score": 0.9,
                "completeness_score": 0.9,
                "consistency_score": 0.9,
                "fact_usage_score": 0.9,
                "audience_alignment_score": 0.9,
                "length_score": 0.85,
                "reading_level_score": 0.9,
                "overall_score": 0.9,
                "issues": [],
                "strengths": ["Vivid narration", "Clear progression"],
                "recommendations": [],
                "passed": True,
            })

        # Fallback: empty JSON with no required fields (should not happen)
        return _ai_response({})


def _make_node_context(state: WorkflowState) -> NodeContext:
    return NodeContext(
        state=state,
        services={"prompt_executor": FakePromptExecutor()},
    )


@pytest.mark.asyncio
async def test_section_writer_generates_all_sections_from_outline() -> None:
    state = _build_state()
    ctx = _make_node_context(state)
    agent = SectionWriterAgent()

    await agent.execute(ctx)

    sections = state.script.metadata["sections"]
    assert len(sections) == 2
    assert {s["section_id"] for s in sections} == {"s1", "s2"}
    assert all(s["narration"] for s in sections)


@pytest.mark.asyncio
async def test_transition_populates_transitions_for_all_sections() -> None:
    state = _build_state()
    # Pre-populate sections as if section_writer ran
    state.script.metadata["sections"] = [
        {
            "section_id": "s1",
            "title": "The Crash",
            "narration": "The sky didn't just break...",
            "estimated_duration_seconds": 45,
            "word_count": 100,
            "emotion": "dramatic",
        },
        {
            "section_id": "s2",
            "title": "Primal Ingenuity",
            "narration": "Surviving the first week...",
            "estimated_duration_seconds": 50,
            "word_count": 110,
            "emotion": "curious",
        },
    ]
    ctx = _make_node_context(state)
    agent = TransitionAgent()

    await agent.execute(ctx)

    transitions = state.script.metadata["transitions"]
    assert "s1" in transitions["transitions"]
    assert "s2" in transitions["transitions"]

    for s in state.script.metadata["sections"]:
        assert s["transition"]


@pytest.mark.asyncio
async def test_script_review_runs_on_complete_sections() -> None:
    state = _build_state()
    state.script.metadata["sections"] = [
        {
            "section_id": "s1",
            "title": "The Crash",
            "narration": "The sky didn't just break...",
            "estimated_duration_seconds": 45,
            "word_count": 100,
            "emotion": "dramatic",
            "transition": "But surviving the crash was only the beginning...",
        },
        {
            "section_id": "s2",
            "title": "Primal Ingenuity",
            "narration": "Surviving the first week...",
            "estimated_duration_seconds": 50,
            "word_count": 110,
            "emotion": "curious",
        },
    ]
    ctx = _make_node_context(state)
    agent = ScriptReviewAgent()

    await agent.execute(ctx)

    review = state.script.metadata["review"]
    assert review["passed"] is True
    assert review["overall_score"] > 0.7
    assert state.script.quality_score == review["overall_score"]


@pytest.mark.asyncio
async def test_section_writer_prompt_contains_all_sections() -> None:
    """Sanity check that the section writer prompt lists every outline section."""
    state = _build_state()
    captured = {}

    class CapturingPromptExecutor:
        async def execute_template(
            self, template, variables, *, agent_name: str = "", options=None
        ):
            if agent_name == "section_writer":
                captured["variables"] = variables
            return _ai_response({
                "sections": [
                    {
                        "section_id": "s1",
                        "title": "The Crash",
                        "narration": "Sky broke.",
                        "estimated_duration_seconds": 45,
                        "word_count": 50,
                    },
                    {
                        "section_id": "s2",
                        "title": "Primal Ingenuity",
                        "narration": "Survival.",
                        "estimated_duration_seconds": 50,
                        "word_count": 60,
                    },
                ]
            })

    ctx = NodeContext(
        state=state,
        services={"prompt_executor": CapturingPromptExecutor()},
    )
    agent = SectionWriterAgent()
    await agent.execute(ctx)

    prompt_vars = captured["variables"]
    assert "s1" in prompt_vars["sections"]
    assert "s2" in prompt_vars["sections"]
    assert "The Crash" in prompt_vars["sections"]
    assert "Primal Ingenuity" in prompt_vars["sections"]
