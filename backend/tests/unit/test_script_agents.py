"""Tests for the Phase 7 Script Generation subsystem."""

from __future__ import annotations

import json
import pytest
from uuid import uuid4

from src.ai.agents.base import AgentResult
from src.ai.agents.context import AgentContext
from src.ai.agents.research.schema import (
    AudienceAnalysisResult,
    AudiencePersona,
    ContentAngle,
    ContentAngleResult,
    FactVerificationResult,
    KeywordSet,
    ResearchPackage,
    ResearchPlan,
    ResearchSummary,
    TopicAnalysis,
    VerifiedFact,
    WebResearchResult,
)
from src.ai.agents.script.call_to_action import CallToActionAgent
from src.ai.agents.script.events import ScriptEventEmitter, ScriptEvents
from src.ai.agents.script.hook_generator import HookGeneratorAgent
from src.ai.agents.script.narrative_strategy import NarrativeStrategyAgent
from src.ai.agents.script.script_optimization import ScriptOptimizationAgent
from src.ai.agents.script.script_outline import ScriptOutlineAgent
from src.ai.agents.script.script_review import ScriptReviewAgent
from src.ai.agents.script.section_writer import SectionWriterAgent
from src.ai.agents.script.transition import TransitionAgent
from src.ai.agents.script.schema import (
    CallToAction,
    CTAResult,
    Hook,
    HookResult,
    NarrativeStrategy,
    OutlineSection,
    ScriptOptimizationResult,
    ScriptOutline,
    ScriptPackage,
    ScriptQualityEvaluation,
    ScriptReviewResult,
    ScriptSection,
    TransitionResult,
)
from src.ai.agents.script.workflow import ScriptWorkflowGraph
from src.core.enums import AgentType
from src.workflow.contexts import (
    CancellationToken,
    ExecutionContext,
    IdentityContext,
    NodeContext,
)
from src.workflow.state import WorkflowState


# ===========================================================================
# Mock LLM Gateway
# ===========================================================================
class MockLLMGateway:
    """Mock LLM gateway that returns pre-configured JSON responses."""

    def __init__(self, response_data: dict | None = None, fail: bool = False) -> None:
        self._response_data = response_data or {}
        self._fail = fail
        self._call_count = 0

    async def generate(self, prompt: str, **kwargs):
        self._call_count += 1
        if self._fail:
            raise Exception("Gateway error")

        class Result:
            success = True
            output = json.dumps(self._response_data)
            cost_usd = 0.05
            input_tokens = 100
            output_tokens = 50
            total_tokens = 150
            latency_ms = 100
            provider = "gemini"
            model = "gemini-2.0-flash"
            metadata = {}
            correlation_id = kwargs.get("correlation_id")

        return Result()

    @property
    def call_count(self) -> int:
        return self._call_count


# ===========================================================================
# Helper to create agent context with research and script state
# ===========================================================================
def make_context(
    *,
    topic: str = "Artificial Intelligence",
    gateway: MockLLMGateway | None = None,
    research_package: ResearchPackage | None = None,
    script_metadata: dict | None = None,
) -> AgentContext:
    state = WorkflowState()
    state.topic.raw_topic = topic
    state.topic.expanded_topic = topic
    state.project.name = topic

    if research_package is None:
        research_package = ResearchPackage(
            topic_analysis=TopicAnalysis(
                raw_topic=topic,
                expanded_topic=topic,
                category="technology",
                content_type="educational",
                target_duration_seconds=600,
            ),
            summary=ResearchSummary(
                overview=f"Overview of {topic}",
                important_facts=["Fact 1", "Fact 2"],
            ),
            fact_verification=FactVerificationResult(
                verified_facts=[VerifiedFact(fact="Verified fact 1", confidence=0.9, verified=True)],
                overall_confidence=0.85,
                total_checked=5,
                total_verified=4,
            ),
            audience=AudienceAnalysisResult(
                primary_persona=AudiencePersona(persona_name="Tech Professional"),
            ),
            content_angle=ContentAngleResult(
                selected_angle=ContentAngle(angle_type="educational", title="Understanding AI"),
            ),
            keywords=KeywordSet(primary_keywords=["AI"]),
        )

    state.research.metadata["research_package"] = research_package.model_dump()

    if script_metadata:
        state.script.metadata = dict(script_metadata)

    return AgentContext(
        state=state,
        agent_name="test",
        agent_type="script_writer",
        gateways={"llm": gateway or MockLLMGateway()},
        identity=IdentityContext(workflow_id="test", execution_id=uuid4()),
    )


# ===========================================================================
# Schema tests
# ===========================================================================
class TestScriptSchemas:
    def test_narrative_strategy_defaults(self):
        ns = NarrativeStrategy()
        assert ns.style == "educational"
        assert ns.pacing == "moderate"
        assert ns.tone == "informative"

    def test_narrative_strategy_with_data(self):
        ns = NarrativeStrategy(
            style="storytelling",
            rationale="Engages audience",
            pacing="varied",
            tone="dramatic",
        )
        assert ns.style == "storytelling"
        assert ns.pacing == "varied"

    def test_outline_section_defaults(self):
        os = OutlineSection()
        assert os.importance == "medium"
        assert os.estimated_time_seconds == 0

    def test_script_outline_with_sections(self):
        outline = ScriptOutline(
            title="Understanding AI",
            sections=[
                OutlineSection(section_id="s1", title="Intro", target_word_count=200),
                OutlineSection(section_id="s2", title="Body", target_word_count=400),
            ],
        )
        assert len(outline.sections) == 2
        assert outline.sections[0].section_id == "s1"

    def test_hook_defaults(self):
        h = Hook()
        assert h.estimated_retention_score == 0.0

    def test_hook_result_with_selected(self):
        hr = HookResult(
            hooks=[Hook(hook_type="question", content="What is AI?", estimated_retention_score=0.8)],
            selected_hook=Hook(hook_type="question", content="What is AI?", estimated_retention_score=0.8),
        )
        assert hr.selected_hook is not None
        assert hr.selected_hook.hook_type == "question"

    def test_script_section_defaults(self):
        ss = ScriptSection()
        assert ss.emotion == ""
        assert ss.importance == "medium"
        assert ss.future_scene_count == 0

    def test_script_section_with_data(self):
        ss = ScriptSection(
            section_id="s1",
            title="Introduction",
            narration="Welcome to this video about AI.",
            word_count=7,
            emotion="excited",
            importance="high",
        )
        assert ss.narration != ""
        assert ss.word_count == 7

    def test_transition_result(self):
        tr = TransitionResult(
            transitions={"s1": "Now let's look at..."},
            smoothness_score=0.85,
        )
        assert "s1" in tr.transitions
        assert tr.smoothness_score == 0.85

    def test_call_to_action(self):
        cta = CallToAction(cta_type="subscribe", content="Subscribe for more!")
        assert cta.cta_type == "subscribe"
        assert cta.placement == "end"

    def test_cta_result(self):
        cr = CTAResult(
            ctas=[CallToAction(cta_type="subscribe", content="Subscribe!")],
            primary_cta=CallToAction(cta_type="subscribe", content="Subscribe!"),
        )
        assert cr.primary_cta is not None
        assert len(cr.ctas) == 1

    def test_script_review_result(self):
        rr = ScriptReviewResult(
            overall_score=0.85,
            passed=True,
            issues=["Issue 1"],
            strengths=["Strength 1"],
        )
        assert rr.passed is True
        assert rr.overall_score == 0.85

    def test_script_optimization_result(self):
        opt = ScriptOptimizationResult(
            optimized_content="Optimized script text",
            engagement_score=0.88,
            changes_made=["Improved hook", "Reduced repetition"],
        )
        assert opt.optimized_content != ""
        assert len(opt.changes_made) == 2

    def test_script_quality_evaluation(self):
        qe = ScriptQualityEvaluation(
            retention_potential=0.85,
            overall_score=0.82,
        )
        assert qe.retention_potential == 0.85

    def test_script_package_defaults(self):
        sp = ScriptPackage()
        assert sp.word_count == 0
        assert sp.version == 1
        assert sp.is_ready is False

    def test_script_package_ready(self):
        sp = ScriptPackage(
            full_script="Full script content",
            title="Test Script",
            sections=[ScriptSection(section_id="s1", narration="Content", word_count=100)],
            word_count=100,
        )
        assert sp.is_ready is True

    def test_script_package_section_count(self):
        sp = ScriptPackage(
            sections=[
                ScriptSection(section_id="s1"),
                ScriptSection(section_id="s2"),
                ScriptSection(section_id="s3"),
            ],
        )
        assert sp.section_count == 3

    def test_script_package_all_references(self):
        sp = ScriptPackage(
            references=["ref1"],
            outline=ScriptOutline(references=["ref2"]),
            sections=[ScriptSection(references=["ref3"])],
        )
        refs = sp.all_references
        assert "ref1" in refs
        assert "ref2" in refs
        assert "ref3" in refs

    def test_script_package_assemble_full_script(self):
        sp = ScriptPackage(
            hook_result=HookResult(
                selected_hook=Hook(content="Hook text"),
            ),
            sections=[
                ScriptSection(section_id="s1", narration="Section 1 content", transition="Now..."),
                ScriptSection(section_id="s2", narration="Section 2 content"),
            ],
            cta_result=CTAResult(
                primary_cta=CallToAction(content="Subscribe!"),
            ),
        )
        full = sp.assemble_full_script()
        assert "Hook text" in full
        assert "Section 1 content" in full
        assert "Now..." in full
        assert "Section 2 content" in full
        assert "Subscribe!" in full


# ===========================================================================
# Narrative Strategy Agent tests
# ===========================================================================
class TestNarrativeStrategyAgent:
    @pytest.mark.asyncio
    async def test_successful_strategy(self):
        gateway = MockLLMGateway(response_data={
            "style": "storytelling",
            "rationale": "Engages audience emotionally",
            "flow": "Start with a story, then explain concepts",
            "pacing": "varied",
            "tone": "dramatic",
            "emotional_arc": "Curiosity to understanding",
            "key_beats": ["Hook", "Problem", "Solution"],
            "audience_alignment": "Matches tech professionals",
        })
        agent = NarrativeStrategyAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway)
        result = await agent.run_agent(ctx)
        assert result.success is True
        ns_data = ctx.state.script.metadata.get("narrative_strategy")
        assert ns_data is not None
        assert ns_data["style"] == "storytelling"

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = NarrativeStrategyAgent()
        assert agent.agent_type == AgentType.SCRIPT_WRITER

    @pytest.mark.asyncio
    async def test_cancellation(self):
        gateway = MockLLMGateway()
        agent = NarrativeStrategyAgent()
        token = CancellationToken()
        token.cancel()
        ctx = make_context(gateway=gateway)
        ctx.cancellation_token = token
        result = await agent.run_agent(ctx)
        assert result.success is False


# ===========================================================================
# Script Outline Agent tests
# ===========================================================================
class TestScriptOutlineAgent:
    @pytest.mark.asyncio
    async def test_successful_outline(self):
        gateway = MockLLMGateway(response_data={
            "title": "Understanding AI",
            "opening": "Opening description",
            "sections": [
                {
                    "section_id": "s1",
                    "title": "Introduction",
                    "description": "Intro to AI",
                    "key_talking_points": ["What is AI", "Why it matters"],
                    "estimated_time_seconds": 60,
                    "target_word_count": 150,
                    "importance": "high",
                },
                {
                    "section_id": "s2",
                    "title": "How AI Works",
                    "description": "Technical overview",
                    "estimated_time_seconds": 120,
                    "target_word_count": 300,
                    "importance": "critical",
                },
            ],
            "closing": "Closing description",
            "total_estimated_time_seconds": 180,
            "total_target_word_count": 450,
            "references": ["ref1"],
        })
        agent = ScriptOutlineAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, script_metadata={
            "narrative_strategy": NarrativeStrategy(style="educational").model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        outline_data = ctx.state.script.metadata.get("script_outline")
        assert outline_data is not None
        assert outline_data["title"] == "Understanding AI"
        assert len(outline_data["sections"]) == 2
        assert ctx.state.script.title == "Understanding AI"

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = ScriptOutlineAgent()
        assert agent.agent_type == AgentType.SCRIPT_WRITER


# ===========================================================================
# Hook Generator Agent tests
# ===========================================================================
class TestHookGeneratorAgent:
    @pytest.mark.asyncio
    async def test_successful_hook_generation(self):
        gateway = MockLLMGateway(response_data={
            "hooks": [
                {"hook_type": "question", "content": "What if AI could think?", "estimated_retention_score": 0.85},
                {"hook_type": "bold_statement", "content": "AI will change everything!", "estimated_retention_score": 0.75},
                {"hook_type": "unexpected_fact", "content": "AI was coined in 1956.", "estimated_retention_score": 0.7},
                {"hook_type": "story", "content": "Once upon a time...", "estimated_retention_score": 0.65},
                {"hook_type": "contradiction", "content": "AI is both smart and dumb.", "estimated_retention_score": 0.8},
                {"hook_type": "curiosity_gap", "content": "The truth about AI is...", "estimated_retention_score": 0.9},
            ],
        })
        agent = HookGeneratorAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, script_metadata={
            "narrative_strategy": NarrativeStrategy(style="storytelling").model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        hook_data = ctx.state.script.metadata.get("hook_result")
        assert hook_data is not None
        assert len(hook_data["hooks"]) == 6
        assert hook_data["selected_hook"]["hook_type"] == "curiosity_gap"
        assert ctx.state.script.hook != ""

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = HookGeneratorAgent()
        assert agent.agent_type == AgentType.SCRIPT_WRITER


# ===========================================================================
# Section Writer Agent tests
# ===========================================================================
class TestSectionWriterAgent:
    @pytest.mark.asyncio
    async def test_successful_section_writing(self):
        gateway = MockLLMGateway(response_data={
            "sections": [
                {
                    "section_id": "s1",
                    "title": "Introduction",
                    "narration": "Welcome to this video about AI. Today we'll explore...",
                    "estimated_duration_seconds": 60,
                    "word_count": 150,
                    "emotion": "excited",
                    "importance": "high",
                    "purpose": "inform",
                    "references": ["ref1"],
                    "facts_used": ["AI was coined in 1956"],
                    "examples": ["Siri"],
                    "future_scene_count": 3,
                }
            ]
        })
        agent = SectionWriterAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, script_metadata={
            "narrative_strategy": NarrativeStrategy(style="educational").model_dump(),
            "script_outline": ScriptOutline(
                sections=[OutlineSection(section_id="s1", title="Introduction", target_word_count=150)],
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        sections_data = ctx.state.script.metadata.get("sections")
        assert sections_data is not None
        assert len(sections_data) == 1
        assert sections_data[0]["section_id"] == "s1"

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = SectionWriterAgent()
        assert agent.agent_type == AgentType.SCRIPT_WRITER


# ===========================================================================
# Transition Agent tests
# ===========================================================================
class TestTransitionAgent:
    @pytest.mark.asyncio
    async def test_successful_transitions(self):
        gateway = MockLLMGateway(response_data={
            "transitions": {
                "s1": "Now that we understand the basics, let's dive deeper...",
                "s2": "Moving on to practical applications...",
            },
            "flow_analysis": "Sections flow naturally from concept to application",
            "smoothness_score": 0.85,
        })
        agent = TransitionAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, script_metadata={
            "narrative_strategy": NarrativeStrategy(style="educational").model_dump(),
            "sections": [
                ScriptSection(section_id="s1", title="Intro", narration="Content 1").model_dump(),
                ScriptSection(section_id="s2", title="Body", narration="Content 2").model_dump(),
            ],
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        trans_data = ctx.state.script.metadata.get("transitions")
        assert trans_data is not None
        assert "s1" in trans_data["transitions"]
        assert trans_data["smoothness_score"] == 0.85

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = TransitionAgent()
        assert agent.agent_type == AgentType.SCRIPT_WRITER


# ===========================================================================
# Call to Action Agent tests
# ===========================================================================
class TestCallToActionAgent:
    @pytest.mark.asyncio
    async def test_successful_cta(self):
        gateway = MockLLMGateway(response_data={
            "ctas": [
                {"cta_type": "subscribe", "content": "Subscribe for more AI content!", "placement": "end"},
                {"cta_type": "like", "content": "Like if you learned something!", "placement": "end"},
            ],
            "primary_cta": {
                "cta_type": "subscribe",
                "content": "Subscribe for more AI content!",
                "placement": "end",
                "rationale": "Most important for channel growth",
            },
            "secondary_ctas": [
                {"cta_type": "like", "content": "Like if you learned something!", "placement": "end"},
            ],
            "channel_style_match": "Matches educational channel style",
        })
        agent = CallToActionAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, script_metadata={
            "narrative_strategy": NarrativeStrategy(style="educational").model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        cta_data = ctx.state.script.metadata.get("cta_result")
        assert cta_data is not None
        assert cta_data["primary_cta"]["cta_type"] == "subscribe"
        assert ctx.state.script.outro != ""

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = CallToActionAgent()
        assert agent.agent_type == AgentType.SCRIPT_WRITER


# ===========================================================================
# Script Review Agent tests
# ===========================================================================
class TestScriptReviewAgent:
    @pytest.mark.asyncio
    async def test_successful_review(self):
        gateway = MockLLMGateway(response_data={
            "logic_score": 0.85,
            "flow_score": 0.8,
            "completeness_score": 0.9,
            "consistency_score": 0.85,
            "fact_usage_score": 0.8,
            "audience_alignment_score": 0.9,
            "length_score": 0.75,
            "reading_level_score": 0.85,
            "overall_score": 0.84,
            "issues": ["Hook could be stronger"],
            "strengths": ["Good flow", "Clear explanations"],
            "recommendations": ["Add more examples"],
            "passed": True,
        })
        agent = ScriptReviewAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, script_metadata={
            "hook_result": HookResult(
                selected_hook=Hook(content="Hook text"),
            ).model_dump(),
            "sections": [
                ScriptSection(section_id="s1", title="Intro", narration="Content", word_count=100).model_dump(),
            ],
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        review_data = ctx.state.script.metadata.get("review")
        assert review_data is not None
        assert review_data["overall_score"] == 0.84
        assert review_data["passed"] is True
        assert ctx.state.script.quality_score == 0.84

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = ScriptReviewAgent()
        assert agent.agent_type == AgentType.SCRIPT_WRITER


# ===========================================================================
# Script Optimization Agent tests
# ===========================================================================
class TestScriptOptimizationAgent:
    @pytest.mark.asyncio
    async def test_successful_optimization(self):
        gateway = MockLLMGateway(response_data={
            "optimized_content": "Optimized full script text with better flow and engagement.",
            "retention_improvement": 0.15,
            "clarity_improvement": 0.1,
            "redundancy_reduction": 0.2,
            "sentence_variety_score": 0.85,
            "natural_speech_score": 0.9,
            "engagement_score": 0.88,
            "changes_made": ["Improved hook", "Reduced repetition", "Added transitions"],
            "optimized_sections": [
                {
                    "section_id": "s1",
                    "title": "Introduction",
                    "narration": "Optimized intro narration",
                    "estimated_duration_seconds": 60,
                    "word_count": 150,
                    "emotion": "excited",
                    "importance": "high",
                    "purpose": "inform",
                },
            ],
        })
        agent = ScriptOptimizationAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, script_metadata={
            "narrative_strategy": NarrativeStrategy(style="educational").model_dump(),
            "script_outline": ScriptOutline(title="Understanding AI").model_dump(),
            "hook_result": HookResult(
                selected_hook=Hook(content="Hook text"),
            ).model_dump(),
            "sections": [
                ScriptSection(section_id="s1", title="Intro", narration="Original content", word_count=100).model_dump(),
            ],
            "transitions": TransitionResult(transitions={"s1": "Now..."}).model_dump(),
            "cta_result": CTAResult(
                primary_cta=CallToAction(content="Subscribe!"),
            ).model_dump(),
            "review": ScriptReviewResult(
                overall_score=0.8,
                passed=True,
                issues=["Minor issue"],
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        opt_data = ctx.state.script.metadata.get("optimization")
        assert opt_data is not None
        assert opt_data["engagement_score"] == 0.88
        assert len(opt_data["changes_made"]) == 3

    @pytest.mark.asyncio
    async def test_assembles_script_package(self):
        gateway = MockLLMGateway(response_data={
            "optimized_content": "Optimized script",
            "engagement_score": 0.88,
            "changes_made": ["Improved flow"],
            "optimized_sections": [
                {"section_id": "s1", "title": "Intro", "narration": "Optimized", "word_count": 100, "estimated_duration_seconds": 60},
            ],
        })
        agent = ScriptOptimizationAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, script_metadata={
            "narrative_strategy": NarrativeStrategy(style="educational").model_dump(),
            "script_outline": ScriptOutline(title="Understanding AI").model_dump(),
            "hook_result": HookResult(
                selected_hook=Hook(content="Hook text"),
            ).model_dump(),
            "sections": [
                ScriptSection(section_id="s1", title="Intro", narration="Content", word_count=100).model_dump(),
            ],
            "transitions": TransitionResult().model_dump(),
            "cta_result": CTAResult(
                primary_cta=CallToAction(content="Subscribe!"),
            ).model_dump(),
            "review": ScriptReviewResult(
                overall_score=0.85,
                passed=True,
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        package_data = ctx.state.script.metadata.get("script_package")
        assert package_data is not None
        assert package_data["title"] == "Understanding AI"
        assert package_data["quality"]["overall_score"] == 0.85
        assert ctx.state.script.content == "Optimized script"

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = ScriptOptimizationAgent()
        assert agent.agent_type == AgentType.SCRIPT_WRITER


# ===========================================================================
# Script Workflow Graph tests
# ===========================================================================
class TestScriptWorkflowGraph:
    def test_build_graph(self):
        graph = ScriptWorkflowGraph()
        graph.build_graph()
        assert len(graph.nodes) == 8

    def test_graph_metadata(self):
        graph = ScriptWorkflowGraph()
        graph.build_graph()
        meta = graph.metadata
        assert meta.name == "script_workflow"
        assert meta.entry_node == "narrative_strategy"
        assert "script_optimization" in meta.exit_nodes

    def test_graph_has_all_agents(self):
        graph = ScriptWorkflowGraph()
        graph.build_graph()
        expected_nodes = {
            "narrative_strategy",
            "script_outline",
            "hook_generator",
            "section_writer",
            "transition",
            "cta",
            "script_review",
            "script_optimization",
        }
        assert set(graph.nodes.keys()) == expected_nodes

    def test_graph_edges_sequential(self):
        graph = ScriptWorkflowGraph()
        graph.build_graph()
        edges = graph.edges
        assert len(edges) == 7  # 8 nodes, 7 edges

    def test_graph_edge_chain(self):
        graph = ScriptWorkflowGraph()
        graph.build_graph()
        edges = graph.edges
        chain = [(e.source, e.target) for e in edges]
        assert ("narrative_strategy", "script_outline") in chain
        assert ("script_outline", "hook_generator") in chain
        assert ("hook_generator", "section_writer") in chain
        assert ("section_writer", "transition") in chain
        assert ("transition", "cta") in chain
        assert ("cta", "script_review") in chain
        assert ("script_review", "script_optimization") in chain


# ===========================================================================
# Script Events tests
# ===========================================================================
class TestScriptEvents:
    @pytest.mark.asyncio
    async def test_emit_script_started(self):
        emitter = ScriptEventEmitter(event_bus=None)
        await emitter.emit_script_started("AI", uuid4())

    @pytest.mark.asyncio
    async def test_emit_narrative_strategy_selected(self):
        emitter = ScriptEventEmitter(event_bus=None)
        await emitter.emit_narrative_strategy_selected("storytelling", "Engages audience")

    @pytest.mark.asyncio
    async def test_emit_outline_generated(self):
        emitter = ScriptEventEmitter(event_bus=None)
        await emitter.emit_outline_generated(5, 600)

    @pytest.mark.asyncio
    async def test_emit_hook_selected(self):
        emitter = ScriptEventEmitter(event_bus=None)
        await emitter.emit_hook_selected("curiosity_gap", 0.9)

    @pytest.mark.asyncio
    async def test_emit_sections_generated(self):
        emitter = ScriptEventEmitter(event_bus=None)
        await emitter.emit_sections_generated(5, 1500)

    @pytest.mark.asyncio
    async def test_emit_transitions_generated(self):
        emitter = ScriptEventEmitter(event_bus=None)
        await emitter.emit_transitions_generated(4, 0.85)

    @pytest.mark.asyncio
    async def test_emit_cta_generated(self):
        emitter = ScriptEventEmitter(event_bus=None)
        await emitter.emit_cta_generated(3, "subscribe")

    @pytest.mark.asyncio
    async def test_emit_script_reviewed(self):
        emitter = ScriptEventEmitter(event_bus=None)
        await emitter.emit_script_reviewed(0.85, True, 2)

    @pytest.mark.asyncio
    async def test_emit_script_optimized(self):
        emitter = ScriptEventEmitter(event_bus=None)
        await emitter.emit_script_optimized(5, 0.88)

    @pytest.mark.asyncio
    async def test_emit_script_completed(self):
        emitter = ScriptEventEmitter(event_bus=None)
        await emitter.emit_script_completed(uuid4(), 1500, 600, 0.85)

    def test_script_event_constants(self):
        assert ScriptEvents.SCRIPT_STARTED == "ScriptStarted"
        assert ScriptEvents.NARRATIVE_STRATEGY_SELECTED == "NarrativeStrategySelected"
        assert ScriptEvents.OUTLINE_GENERATED == "OutlineGenerated"
        assert ScriptEvents.HOOK_SELECTED == "HookSelected"
        assert ScriptEvents.SECTIONS_GENERATED == "SectionsGenerated"
        assert ScriptEvents.TRANSITIONS_GENERATED == "TransitionsGenerated"
        assert ScriptEvents.CTA_GENERATED == "CTAGenerated"
        assert ScriptEvents.SCRIPT_REVIEWED == "ScriptReviewed"
        assert ScriptEvents.SCRIPT_OPTIMIZED == "ScriptOptimized"
        assert ScriptEvents.SCRIPT_COMPLETED == "ScriptCompleted"


# ===========================================================================
# Prompt Template tests
# ===========================================================================
class TestScriptPrompts:
    def test_narrative_strategy_prompt(self):
        from src.ai.agents.script.prompts import NARRATIVE_STRATEGY_PROMPT
        assert NARRATIVE_STRATEGY_PROMPT.name == "narrative_strategy"
        assert "{{topic}}" in NARRATIVE_STRATEGY_PROMPT.template

    def test_script_outline_prompt(self):
        from src.ai.agents.script.prompts import SCRIPT_OUTLINE_PROMPT
        assert SCRIPT_OUTLINE_PROMPT.name == "script_outline"
        assert "{{narrative_style}}" in SCRIPT_OUTLINE_PROMPT.template

    def test_hook_generator_prompt(self):
        from src.ai.agents.script.prompts import HOOK_GENERATOR_PROMPT
        assert HOOK_GENERATOR_PROMPT.name == "hook_generator"
        assert "{{narrative_style}}" in HOOK_GENERATOR_PROMPT.template

    def test_section_writer_prompt(self):
        from src.ai.agents.script.prompts import SECTION_WRITER_PROMPT
        assert SECTION_WRITER_PROMPT.name == "section_writer"
        assert "{{sections}}" in SECTION_WRITER_PROMPT.template

    def test_transition_prompt(self):
        from src.ai.agents.script.prompts import TRANSITION_PROMPT
        assert TRANSITION_PROMPT.name == "transition"
        assert "{{sections}}" in TRANSITION_PROMPT.template

    def test_cta_prompt(self):
        from src.ai.agents.script.prompts import CTA_PROMPT
        assert CTA_PROMPT.name == "cta"
        assert "{{channel_style}}" in CTA_PROMPT.template

    def test_script_review_prompt(self):
        from src.ai.agents.script.prompts import SCRIPT_REVIEW_PROMPT
        assert SCRIPT_REVIEW_PROMPT.name == "script_review"
        assert "{{full_script}}" in SCRIPT_REVIEW_PROMPT.template

    def test_script_optimization_prompt(self):
        from src.ai.agents.script.prompts import SCRIPT_OPTIMIZATION_PROMPT
        assert SCRIPT_OPTIMIZATION_PROMPT.name == "script_optimization"
        assert "{{full_script}}" in SCRIPT_OPTIMIZATION_PROMPT.template

    def test_all_prompts_registered(self):
        from src.ai.agents.script.prompts import SCRIPT_PROMPTS
        assert len(SCRIPT_PROMPTS) == 8
        for name in ["narrative_strategy", "script_outline", "hook_generator",
                      "section_writer", "transition", "cta", "script_review", "script_optimization"]:
            assert name in SCRIPT_PROMPTS

    def test_all_prompts_have_versions(self):
        from src.ai.agents.script.prompts import SCRIPT_PROMPTS
        for name, template in SCRIPT_PROMPTS.items():
            assert template.version != "", f"Prompt {name} has no version"


# ===========================================================================
# Integration test — full script pipeline
# ===========================================================================
class TestScriptPipelineIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test the full script generation pipeline with all 8 agents."""
        responses = iter([
            # Narrative Strategy
            {"style": "educational", "rationale": "Best for topic", "flow": "Start simple, go deep", "pacing": "moderate", "tone": "informative", "key_beats": ["Hook", "Explain", "Conclude"]},
            # Script Outline
            {"title": "Understanding AI", "opening": "Opening", "sections": [{"section_id": "s1", "title": "Intro", "description": "Intro", "estimated_time_seconds": 60, "target_word_count": 150, "importance": "high"}], "closing": "Closing", "total_estimated_time_seconds": 60, "total_target_word_count": 150, "references": []},
            # Hook Generator
            {"hooks": [{"hook_type": "question", "content": "What is AI?", "estimated_retention_score": 0.85}, {"hook_type": "curiosity_gap", "content": "The truth about AI...", "estimated_retention_score": 0.9}]},
            # Section Writer
            {"sections": [{"section_id": "s1", "title": "Intro", "narration": "Welcome to this video about AI. Today we'll explore what AI is and why it matters.", "estimated_duration_seconds": 60, "word_count": 20, "emotion": "excited", "importance": "high", "purpose": "inform", "facts_used": ["AI is powerful"], "examples": [], "future_scene_count": 2}]},
            # Transition
            {"transitions": {"s1": "Now let's dive deeper..."}, "flow_analysis": "Good flow", "smoothness_score": 0.85},
            # CTA
            {"ctas": [{"cta_type": "subscribe", "content": "Subscribe!", "placement": "end"}], "primary_cta": {"cta_type": "subscribe", "content": "Subscribe!", "placement": "end", "rationale": "Growth"}, "secondary_ctas": [], "channel_style_match": "Good"},
            # Script Review
            {"logic_score": 0.85, "flow_score": 0.8, "completeness_score": 0.9, "consistency_score": 0.85, "fact_usage_score": 0.8, "audience_alignment_score": 0.9, "length_score": 0.75, "reading_level_score": 0.85, "overall_score": 0.84, "issues": [], "strengths": ["Good flow"], "recommendations": [], "passed": True},
            # Script Optimization
            {"optimized_content": "Optimized script content", "retention_improvement": 0.15, "clarity_improvement": 0.1, "redundancy_reduction": 0.2, "sentence_variety_score": 0.85, "natural_speech_score": 0.9, "engagement_score": 0.88, "changes_made": ["Improved hook"], "optimized_sections": [{"section_id": "s1", "title": "Intro", "narration": "Optimized intro", "word_count": 150, "estimated_duration_seconds": 60, "emotion": "excited", "importance": "high", "purpose": "inform"}]},
        ])

        class PipelineGateway:
            async def generate(self, prompt, **kwargs):
                class Result:
                    success = True
                    output = json.dumps(next(responses))
                    cost_usd = 0.05
                    input_tokens = 100
                    output_tokens = 50
                    total_tokens = 150
                    latency_ms = 100
                    provider = "gemini"
                    model = "gemini-2.0-flash"
                    metadata = {}
                    correlation_id = kwargs.get("correlation_id")
                return Result()

        gateway = PipelineGateway()
        ctx = make_context(gateway=gateway)

        agents = [
            NarrativeStrategyAgent(),
            ScriptOutlineAgent(),
            HookGeneratorAgent(),
            SectionWriterAgent(),
            TransitionAgent(),
            CallToActionAgent(),
            ScriptReviewAgent(),
            ScriptOptimizationAgent(),
        ]

        for agent in agents:
            agent.enable_quality_check = False
            agent.enable_artifact_creation = False

        for agent in agents:
            result = await agent.run_agent(ctx)
            assert result.success is True, f"Agent {agent.name} failed: {result.error}"

        # Verify final script package
        package_data = ctx.state.script.metadata.get("script_package")
        assert package_data is not None
        assert package_data["title"] == "Understanding AI"
        assert package_data["quality"]["overall_score"] == 0.84
        assert package_data["optimization"]["engagement_score"] == 0.88
        assert ctx.state.script.content == "Optimized script content"
