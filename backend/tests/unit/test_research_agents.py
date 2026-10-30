"""Tests for the Phase 6 Topic Discovery & Research subsystem."""

from __future__ import annotations

import json
import pytest
from uuid import uuid4

from src.ai.agents.base import AgentResult
from src.ai.agents.context import AgentContext
from src.ai.agents.research.audience_analysis import AudienceAnalysisAgent
from src.ai.agents.research.content_angle import ContentAngleAgent
from src.ai.agents.research.events import ResearchEventEmitter, ResearchEvents
from src.ai.agents.research.fact_verification import FactVerificationAgent
from src.ai.agents.research.keyword_extraction import KeywordExtractionAgent
from src.ai.agents.research.research_agent import ResearchAgent
from src.ai.agents.research.research_planner import ResearchPlannerAgent
from src.ai.agents.research.research_summary import ResearchSummaryAgent
from src.ai.agents.research.schema import (
    AudienceAnalysisResult,
    AudiencePersona,
    ContentAngle,
    ContentAngleResult,
    FactVerificationResult,
    KeywordSet,
    ResearchFact,
    ResearchPackage,
    ResearchPlan,
    ResearchSection,
    ResearchSummary,
    SearchQuery,
    TopicAnalysis,
    VerifiedFact,
    WebResearchResult,
)
from src.ai.agents.research.topic_analyzer import TopicAnalyzerAgent
from src.ai.agents.research.workflow import ResearchWorkflowGraph
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
# Helper to create agent context with research state
# ===========================================================================
def make_context(
    *,
    topic: str = "Artificial Intelligence",
    gateway: MockLLMGateway | None = None,
    research_metadata: dict | None = None,
) -> AgentContext:
    state = WorkflowState()
    state.topic.raw_topic = topic
    state.project.name = topic
    if research_metadata:
        state.research.metadata = dict(research_metadata)
    return AgentContext(
        state=state,
        agent_name="test",
        agent_type="research",
        gateways={"llm": gateway or MockLLMGateway()},
        identity=IdentityContext(workflow_id="test", execution_id=uuid4()),
    )


# ===========================================================================
# Schema tests
# ===========================================================================
class TestResearchSchemas:
    def test_topic_analysis_defaults(self):
        ta = TopicAnalysis()
        assert ta.difficulty == "intermediate"
        assert ta.content_type == "educational"
        assert ta.longevity == "evergreen"
        assert ta.research_depth == "standard"

    def test_topic_analysis_with_data(self):
        ta = TopicAnalysis(
            raw_topic="AI",
            expanded_topic="Artificial Intelligence in 2024",
            category="technology",
            difficulty="advanced",
            content_type="educational",
        )
        assert ta.category == "technology"
        assert ta.difficulty == "advanced"

    def test_research_plan_with_sections(self):
        plan = ResearchPlan(
            strategy="comprehensive",
            sections=[
                ResearchSection(
                    title="Overview",
                    queries=[SearchQuery(query="what is AI", priority=1)],
                ),
            ],
        )
        assert len(plan.sections) == 1
        assert plan.sections[0].queries[0].query == "what is AI"

    def test_research_fact(self):
        fact = ResearchFact(
            fact="AI was coined in 1956",
            category="historical_event",
            confidence=0.9,
        )
        assert fact.confidence == 0.9
        assert fact.verified is False

    def test_web_research_result(self):
        result = WebResearchResult(
            query="AI",
            facts=[ResearchFact(fact="AI is powerful", confidence=0.8)],
            total_results=1,
        )
        assert len(result.facts) == 1
        assert result.total_results == 1

    def test_verified_fact(self):
        vf = VerifiedFact(
            fact="Test fact",
            confidence=0.95,
            verified=True,
            source_count=3,
        )
        assert vf.verified is True
        assert vf.source_count == 3

    def test_fact_verification_result(self):
        fvr = FactVerificationResult(
            verified_facts=[VerifiedFact(fact="Verified", verified=True)],
            overall_confidence=0.85,
            total_checked=10,
            total_verified=8,
        )
        assert fvr.total_verified == 8
        assert fvr.overall_confidence == 0.85

    def test_keyword_set(self):
        ks = KeywordSet(
            primary_keywords=["AI", "machine learning"],
            secondary_keywords=["neural networks", "deep learning"],
            long_tail_keywords=["how does AI work", "types of machine learning"],
        )
        assert len(ks.primary_keywords) == 2

    def test_audience_persona(self):
        p = AudiencePersona(
            persona_name="Tech Enthusiast",
            knowledge_level="intermediate",
            pain_points=["too much jargon"],
        )
        assert p.persona_name == "Tech Enthusiast"
        assert p.knowledge_level == "intermediate"

    def test_audience_analysis_result(self):
        ar = AudienceAnalysisResult(
            primary_persona=AudiencePersona(persona_name="Student"),
            engagement_drivers=["practical examples"],
        )
        assert ar.primary_persona.persona_name == "Student"

    def test_content_angle(self):
        ca = ContentAngle(
            angle_type="educational",
            title="Understanding AI",
            estimated_engagement=0.85,
        )
        assert ca.angle_type == "educational"
        assert ca.estimated_engagement == 0.85

    def test_content_angle_result(self):
        car = ContentAngleResult(
            angles=[ContentAngle(angle_type="educational")],
            selected_angle=ContentAngle(angle_type="educational", title="Best"),
        )
        assert len(car.angles) == 1
        assert car.selected_angle is not None

    def test_research_summary(self):
        rs = ResearchSummary(
            overview="AI is a broad field...",
            important_facts=["AI was coined in 1956"],
            key_takeaways=["AI is transforming industries"],
        )
        assert rs.overview != ""
        assert len(rs.important_facts) == 1

    def test_research_package_defaults(self):
        rp = ResearchPackage()
        assert rp.confidence_score == 0.0
        assert rp.version == 1
        assert rp.is_ready is False

    def test_research_package_ready(self):
        rp = ResearchPackage(
            topic_analysis=TopicAnalysis(expanded_topic="AI"),
            summary=ResearchSummary(overview="AI overview"),
            fact_verification=FactVerificationResult(
                verified_facts=[VerifiedFact(fact="test", verified=True)],
            ),
            confidence_score=0.85,
        )
        assert rp.is_ready is True

    def test_research_package_all_keywords(self):
        rp = ResearchPackage(
            keywords=KeywordSet(
                primary_keywords=["AI"],
                secondary_keywords=["ML"],
                semantic_keywords=["neural"],
                long_tail_keywords=["how AI works"],
            ),
        )
        all_kw = rp.all_keywords
        assert "AI" in all_kw
        assert "ML" in all_kw
        assert "neural" in all_kw
        assert "how AI works" in all_kw

    def test_research_package_all_references(self):
        rp = ResearchPackage(
            summary=ResearchSummary(references=["ref1", "ref2"]),
            web_research=WebResearchResult(references=["ref2", "ref3"]),
            fact_verification=FactVerificationResult(
                verified_facts=[VerifiedFact(fact="test", sources=["ref4"])],
            ),
        )
        refs = rp.all_references
        assert "ref1" in refs
        assert "ref2" in refs
        assert "ref3" in refs
        assert "ref4" in refs


# ===========================================================================
# Topic Analyzer Agent tests
# ===========================================================================
class TestTopicAnalyzerAgent:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        gateway = MockLLMGateway(response_data={
            "expanded_topic": "AI in Modern Software Development",
            "category": "technology",
            "subcategory": "software engineering",
            "difficulty": "intermediate",
            "content_type": "educational",
            "longevity": "evergreen",
            "target_duration_seconds": 600,
            "research_depth": "deep",
            "user_intent": "Learn about AI tools for developers",
            "missing_information": ["latest AI tools", "pricing"],
            "suggested_angles": ["comparison", "tutorial"],
            "language": "en",
        })
        agent = TopicAnalyzerAgent()
        agent.enable_quality_check = False
        ctx = make_context(topic="AI", gateway=gateway)
        result = await agent.run_agent(ctx)
        assert result.success is True
        assert ctx.state.research.metadata.get("topic_analysis") is not None
        ta_data = ctx.state.research.metadata["topic_analysis"]
        assert ta_data["category"] == "technology"
        assert ta_data["expanded_topic"] == "AI in Modern Software Development"

    @pytest.mark.asyncio
    async def test_updates_topic_state(self):
        gateway = MockLLMGateway(response_data={
            "expanded_topic": "Expanded Topic",
            "category": "science",
            "difficulty": "beginner",
            "content_type": "educational",
        })
        agent = TopicAnalyzerAgent()
        agent.enable_quality_check = False
        ctx = make_context(topic="test topic", gateway=gateway)
        await agent.run_agent(ctx)
        assert ctx.state.topic.expanded_topic == "Expanded Topic"

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = TopicAnalyzerAgent()
        assert agent.agent_type == AgentType.TOPIC

    @pytest.mark.asyncio
    async def test_cancellation(self):
        gateway = MockLLMGateway()
        agent = TopicAnalyzerAgent()
        token = CancellationToken()
        token.cancel()
        ctx = make_context(gateway=gateway)
        ctx.cancellation_token = token
        result = await agent.run_agent(ctx)
        assert result.success is False


# ===========================================================================
# Research Planner Agent tests
# ===========================================================================
class TestResearchPlannerAgent:
    @pytest.mark.asyncio
    async def test_successful_planning(self):
        gateway = MockLLMGateway(response_data={
            "strategy": "Multi-source research",
            "sections": [
                {
                    "title": "Overview",
                    "description": "General overview",
                    "priority": 1,
                    "queries": [
                        {"query": "what is AI", "priority": 1, "source_types": ["web"], "expected_results": "definitions"},
                    ],
                    "fact_requirements": ["definition", "history"],
                },
            ],
            "total_queries": 5,
            "source_diversity_required": True,
            "min_sources": 3,
            "max_sources": 10,
        })
        agent = ResearchPlannerAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, research_metadata={
            "topic_analysis": TopicAnalysis(
                expanded_topic="AI",
                category="technology",
                research_depth="deep",
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        plan_data = ctx.state.research.metadata.get("research_plan")
        assert plan_data is not None
        assert plan_data["strategy"] == "Multi-source research"
        assert len(plan_data["sections"]) == 1

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = ResearchPlannerAgent()
        assert agent.agent_type == AgentType.RESEARCH


# ===========================================================================
# Research Agent tests
# ===========================================================================
class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_successful_research(self):
        gateway = MockLLMGateway(response_data={
            "facts": [
                {"fact": "AI was coined in 1956", "source_url": "https://example.com", "category": "historical_event", "confidence": 0.9},
            ],
            "statistics": [
                {"fact": "AI market is $100B", "source_url": "https://stats.com", "category": "statistic", "confidence": 0.85},
            ],
            "examples": [],
            "historical_events": [],
            "definitions": [
                {"fact": "AI is the simulation of human intelligence", "category": "definition", "confidence": 0.95},
            ],
            "references": ["https://example.com", "https://stats.com"],
        })
        agent = ResearchAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, research_metadata={
            "research_plan": ResearchPlan(
                sections=[ResearchSection(queries=[SearchQuery(query="AI")])],
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        web_data = ctx.state.research.metadata.get("web_research")
        assert web_data is not None
        assert len(web_data["facts"]) == 1

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = ResearchAgent()
        assert agent.agent_type == AgentType.RESEARCH

    @pytest.mark.asyncio
    async def test_max_queries_limit(self):
        gateway = MockLLMGateway(response_data={"facts": [], "references": []})
        agent = ResearchAgent(max_queries=1)
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, research_metadata={
            "research_plan": ResearchPlan(
                sections=[
                    ResearchSection(queries=[
                        SearchQuery(query="q1"),
                        SearchQuery(query="q2"),
                        SearchQuery(query="q3"),
                    ]),
                ],
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True


# ===========================================================================
# Fact Verification Agent tests
# ===========================================================================
class TestFactVerificationAgent:
    @pytest.mark.asyncio
    async def test_successful_verification(self):
        gateway = MockLLMGateway(response_data={
            "verified_facts": [
                {"fact": "AI was coined in 1956", "confidence": 0.95, "verified": True, "sources": ["src1", "src2"], "source_count": 2, "category": "historical_event"},
            ],
            "flagged_facts": [
                {"fact": "AI will replace all jobs", "confidence": 0.3, "verified": False, "conflicting": True, "sources": ["src1"], "source_count": 1, "category": "fact"},
            ],
            "removed_facts": ["AI is sentient"],
            "overall_confidence": 0.8,
            "total_checked": 5,
            "total_verified": 3,
            "total_flagged": 1,
            "total_removed": 1,
        })
        agent = FactVerificationAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, research_metadata={
            "web_research": WebResearchResult(
                facts=[ResearchFact(fact="AI was coined in 1956", confidence=0.8)],
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        fv_data = ctx.state.research.metadata.get("fact_verification")
        assert fv_data is not None
        assert fv_data["overall_confidence"] == 0.8
        assert len(fv_data["verified_facts"]) == 1

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = FactVerificationAgent()
        assert agent.agent_type == AgentType.RESEARCH


# ===========================================================================
# Keyword Extraction Agent tests
# ===========================================================================
class TestKeywordExtractionAgent:
    @pytest.mark.asyncio
    async def test_successful_extraction(self):
        gateway = MockLLMGateway(response_data={
            "primary_keywords": ["AI", "machine learning", "artificial intelligence"],
            "secondary_keywords": ["neural networks", "deep learning", "NLP"],
            "semantic_keywords": ["automation", "intelligence", "cognitive"],
            "long_tail_keywords": ["how does AI work", "types of machine learning"],
            "entities": ["OpenAI", "Google", "DeepMind"],
            "concepts": ["intelligence", "learning", "automation"],
            "seo_tags": ["AI", "ML", "artificial intelligence"],
        })
        agent = KeywordExtractionAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, research_metadata={
            "fact_verification": FactVerificationResult(
                verified_facts=[VerifiedFact(fact="AI is powerful")],
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        kw_data = ctx.state.research.metadata.get("keywords")
        assert kw_data is not None
        assert "AI" in kw_data["primary_keywords"]
        assert ctx.state.topic.keywords is not None

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = KeywordExtractionAgent()
        assert agent.agent_type == AgentType.RESEARCH


# ===========================================================================
# Audience Analysis Agent tests
# ===========================================================================
class TestAudienceAnalysisAgent:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        gateway = MockLLMGateway(response_data={
            "primary_persona": {
                "persona_name": "Tech Professional",
                "description": "Software developers interested in AI",
                "knowledge_level": "intermediate",
                "age_range": "25-40",
                "interests": ["AI", "programming", "technology"],
                "pain_points": ["keeping up with AI advances"],
                "questions": ["How can I use AI in my projects?"],
                "reading_level": "advanced",
                "preferred_content_style": "technical with examples",
            },
            "secondary_personas": [],
            "estimated_audience_size": "large",
            "engagement_drivers": ["practical examples", "code snippets"],
        })
        agent = AudienceAnalysisAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, research_metadata={
            "topic_analysis": TopicAnalysis(
                expanded_topic="AI",
                category="technology",
                content_type="educational",
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        aud_data = ctx.state.research.metadata.get("audience")
        assert aud_data is not None
        assert aud_data["primary_persona"]["persona_name"] == "Tech Professional"

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = AudienceAnalysisAgent()
        assert agent.agent_type == AgentType.RESEARCH


# ===========================================================================
# Content Angle Agent tests
# ===========================================================================
class TestContentAngleAgent:
    @pytest.mark.asyncio
    async def test_successful_angle_selection(self):
        gateway = MockLLMGateway(response_data={
            "angles": [
                {"angle_type": "educational", "title": "Understanding AI", "estimated_engagement": 0.85, "difficulty_to_produce": "easy"},
                {"angle_type": "storytelling", "title": "The AI Revolution", "estimated_engagement": 0.75, "difficulty_to_produce": "medium"},
                {"angle_type": "comparison", "title": "AI vs Human Intelligence", "estimated_engagement": 0.7, "difficulty_to_produce": "medium"},
            ],
            "selected_angle": {
                "angle_type": "educational",
                "title": "Understanding AI",
                "description": "A comprehensive guide",
                "rationale": "Best fit for audience",
                "estimated_engagement": 0.85,
                "difficulty_to_produce": "easy",
            },
            "selection_rationale": "Educational angle has highest engagement and lowest difficulty",
        })
        agent = ContentAngleAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, research_metadata={
            "topic_analysis": TopicAnalysis(
                expanded_topic="AI",
                category="technology",
                content_type="educational",
            ).model_dump(),
            "audience": AudienceAnalysisResult(
                primary_persona=AudiencePersona(persona_name="Tech Professional"),
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        angle_data = ctx.state.research.metadata.get("content_angle")
        assert angle_data is not None
        assert len(angle_data["angles"]) == 3
        assert angle_data["selected_angle"]["angle_type"] == "educational"
        assert ctx.state.topic.content_angle == "educational"

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = ContentAngleAgent()
        assert agent.agent_type == AgentType.RESEARCH


# ===========================================================================
# Research Summary Agent tests
# ===========================================================================
class TestResearchSummaryAgent:
    @pytest.mark.asyncio
    async def test_successful_summary(self):
        gateway = MockLLMGateway(response_data={
            "overview": "AI is a broad field of computer science...",
            "important_facts": ["AI was coined in 1956", "ML is a subset of AI"],
            "timeline": ["1956: AI coined", "2010s: Deep learning boom"],
            "examples": ["Siri", "ChatGPT"],
            "statistics": ["AI market: $100B"],
            "warnings": ["AI bias is a concern"],
            "references": ["https://example.com"],
            "suggested_narrative": "Start with history, then applications",
            "key_takeaways": ["AI is transformative", "Ethics matter"],
        })
        agent = ResearchSummaryAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, research_metadata={
            "topic_analysis": TopicAnalysis(expanded_topic="AI").model_dump(),
            "fact_verification": FactVerificationResult(
                verified_facts=[VerifiedFact(fact="AI is powerful", confidence=0.9)],
                overall_confidence=0.85,
                total_checked=5,
                total_verified=4,
            ).model_dump(),
            "audience": AudienceAnalysisResult(
                primary_persona=AudiencePersona(description="Tech professionals"),
            ).model_dump(),
            "content_angle": ContentAngleResult(
                selected_angle=ContentAngle(angle_type="educational", title="Understanding AI"),
            ).model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        summary_data = ctx.state.research.metadata.get("research_summary")
        assert summary_data is not None
        assert "AI is a broad field" in summary_data["overview"]

    @pytest.mark.asyncio
    async def test_assembles_research_package(self):
        gateway = MockLLMGateway(response_data={
            "overview": "AI overview",
            "important_facts": ["Fact 1"],
        })
        agent = ResearchSummaryAgent()
        agent.enable_quality_check = False
        ctx = make_context(gateway=gateway, research_metadata={
            "topic_analysis": TopicAnalysis(expanded_topic="AI").model_dump(),
            "research_plan": ResearchPlan(strategy="test").model_dump(),
            "web_research": WebResearchResult().model_dump(),
            "fact_verification": FactVerificationResult(
                verified_facts=[VerifiedFact(fact="test", verified=True)],
                overall_confidence=0.85,
                total_checked=5,
                total_verified=4,
            ).model_dump(),
            "keywords": KeywordSet(primary_keywords=["AI"]).model_dump(),
            "audience": AudienceAnalysisResult().model_dump(),
            "content_angle": ContentAngleResult().model_dump(),
        })
        result = await agent.run_agent(ctx)
        assert result.success is True
        package_data = ctx.state.research.metadata.get("research_package")
        assert package_data is not None
        assert package_data["confidence_score"] == 0.85
        assert package_data["topic_analysis"]["expanded_topic"] == "AI"

    @pytest.mark.asyncio
    async def test_agent_type(self):
        agent = ResearchSummaryAgent()
        assert agent.agent_type == AgentType.RESEARCH


# ===========================================================================
# Research Workflow Graph tests
# ===========================================================================
class TestResearchWorkflowGraph:
    def test_build_graph(self):
        graph = ResearchWorkflowGraph()
        graph.build_graph()
        assert graph.is_built is False  # build_graph doesn't set _built
        assert len(graph.nodes) == 8

    def test_graph_metadata(self):
        graph = ResearchWorkflowGraph()
        graph.build_graph()
        meta = graph.metadata
        assert meta.name == "research_workflow"
        assert meta.entry_node == "topic_analyzer"
        assert "research_summary" in meta.exit_nodes

    def test_graph_has_all_agents(self):
        graph = ResearchWorkflowGraph()
        graph.build_graph()
        expected_nodes = {
            "topic_analyzer",
            "research_planner",
            "research_agent",
            "fact_verification",
            "keyword_extraction",
            "audience_analysis",
            "content_angle",
            "research_summary",
        }
        assert set(graph.nodes.keys()) == expected_nodes

    def test_graph_edges_sequential(self):
        graph = ResearchWorkflowGraph()
        graph.build_graph()
        edges = graph.edges
        assert len(edges) == 7  # 8 nodes, 7 edges for sequential chain

    def test_graph_edge_chain(self):
        graph = ResearchWorkflowGraph()
        graph.build_graph()
        edges = graph.edges
        chain = [(e.source, e.target) for e in edges]
        assert ("topic_analyzer", "research_planner") in chain
        assert ("research_planner", "research_agent") in chain
        assert ("research_agent", "fact_verification") in chain
        assert ("fact_verification", "keyword_extraction") in chain
        assert ("keyword_extraction", "audience_analysis") in chain
        assert ("audience_analysis", "content_angle") in chain
        assert ("content_angle", "research_summary") in chain


# ===========================================================================
# Research Events tests
# ===========================================================================
class TestResearchEvents:
    @pytest.mark.asyncio
    async def test_emit_research_started(self):
        emitter = ResearchEventEmitter(event_bus=None)
        await emitter.emit_research_started("AI", uuid4())
        # Should not raise

    @pytest.mark.asyncio
    async def test_emit_topic_analyzed(self):
        emitter = ResearchEventEmitter(event_bus=None)
        await emitter.emit_topic_analyzed("AI", "technology", "intermediate")

    @pytest.mark.asyncio
    async def test_emit_research_planned(self):
        emitter = ResearchEventEmitter(event_bus=None)
        await emitter.emit_research_planned(10, 3)

    @pytest.mark.asyncio
    async def test_emit_research_completed(self):
        emitter = ResearchEventEmitter(event_bus=None)
        await emitter.emit_research_completed(50, 15)

    @pytest.mark.asyncio
    async def test_emit_fact_verified(self):
        emitter = ResearchEventEmitter(event_bus=None)
        await emitter.emit_fact_verified(10, 8, 0.85)

    @pytest.mark.asyncio
    async def test_emit_keywords_generated(self):
        emitter = ResearchEventEmitter(event_bus=None)
        await emitter.emit_keywords_generated(5, 25)

    @pytest.mark.asyncio
    async def test_emit_audience_identified(self):
        emitter = ResearchEventEmitter(event_bus=None)
        await emitter.emit_audience_identified("Tech Pro", "intermediate")

    @pytest.mark.asyncio
    async def test_emit_content_angle_selected(self):
        emitter = ResearchEventEmitter(event_bus=None)
        await emitter.emit_content_angle_selected("educational", "Understanding AI")

    @pytest.mark.asyncio
    async def test_emit_research_package_created(self):
        emitter = ResearchEventEmitter(event_bus=None)
        await emitter.emit_research_package_created(uuid4(), 0.85, 10)

    def test_research_event_constants(self):
        assert ResearchEvents.RESEARCH_STARTED == "ResearchStarted"
        assert ResearchEvents.TOPIC_ANALYZED == "TopicAnalyzed"
        assert ResearchEvents.RESEARCH_PLANNED == "ResearchPlanned"
        assert ResearchEvents.RESEARCH_COMPLETED == "ResearchCompleted"
        assert ResearchEvents.FACT_VERIFIED == "FactVerified"
        assert ResearchEvents.KEYWORDS_GENERATED == "KeywordsGenerated"
        assert ResearchEvents.AUDIENCE_IDENTIFIED == "AudienceIdentified"
        assert ResearchEvents.CONTENT_ANGLE_SELECTED == "ContentAngleSelected"
        assert ResearchEvents.RESEARCH_PACKAGE_CREATED == "ResearchPackageCreated"


# ===========================================================================
# Prompt Template tests
# ===========================================================================
class TestResearchPrompts:
    def test_topic_analyzer_prompt(self):
        from src.ai.agents.research.prompts import TOPIC_ANALYZER_PROMPT
        assert TOPIC_ANALYZER_PROMPT.name == "topic_analyzer"
        assert "{{topic}}" in TOPIC_ANALYZER_PROMPT.template

    def test_research_planner_prompt(self):
        from src.ai.agents.research.prompts import RESEARCH_PLANNER_PROMPT
        assert RESEARCH_PLANNER_PROMPT.name == "research_planner"
        assert "{{topic}}" in RESEARCH_PLANNER_PROMPT.template
        assert "{{category}}" in RESEARCH_PLANNER_PROMPT.template

    def test_research_agent_prompt(self):
        from src.ai.agents.research.prompts import RESEARCH_PROMPT
        assert RESEARCH_PROMPT.name == "research_agent"
        assert "{{search_results}}" in RESEARCH_PROMPT.template

    def test_fact_verification_prompt(self):
        from src.ai.agents.research.prompts import FACT_VERIFICATION_PROMPT
        assert FACT_VERIFICATION_PROMPT.name == "fact_verification"
        assert "{{facts}}" in FACT_VERIFICATION_PROMPT.template

    def test_keyword_extraction_prompt(self):
        from src.ai.agents.research.prompts import KEYWORD_EXTRACTION_PROMPT
        assert KEYWORD_EXTRACTION_PROMPT.name == "keyword_extraction"
        assert "{{research_summary}}" in KEYWORD_EXTRACTION_PROMPT.template

    def test_audience_analysis_prompt(self):
        from src.ai.agents.research.prompts import AUDIENCE_ANALYSIS_PROMPT
        assert AUDIENCE_ANALYSIS_PROMPT.name == "audience_analysis"
        assert "{{topic}}" in AUDIENCE_ANALYSIS_PROMPT.template

    def test_content_angle_prompt(self):
        from src.ai.agents.research.prompts import CONTENT_ANGLE_PROMPT
        assert CONTENT_ANGLE_PROMPT.name == "content_angle"
        assert "{{audience}}" in CONTENT_ANGLE_PROMPT.template

    def test_research_summary_prompt(self):
        from src.ai.agents.research.prompts import RESEARCH_SUMMARY_PROMPT
        assert RESEARCH_SUMMARY_PROMPT.name == "research_summary"
        assert "{{verified_facts}}" in RESEARCH_SUMMARY_PROMPT.template

    def test_all_prompts_registered(self):
        from src.ai.agents.research.prompts import RESEARCH_PROMPTS
        assert len(RESEARCH_PROMPTS) == 8
        assert "topic_analyzer" in RESEARCH_PROMPTS
        assert "research_planner" in RESEARCH_PROMPTS
        assert "research_agent" in RESEARCH_PROMPTS
        assert "fact_verification" in RESEARCH_PROMPTS
        assert "keyword_extraction" in RESEARCH_PROMPTS
        assert "audience_analysis" in RESEARCH_PROMPTS
        assert "content_angle" in RESEARCH_PROMPTS
        assert "research_summary" in RESEARCH_PROMPTS

    def test_all_prompts_have_versions(self):
        from src.ai.agents.research.prompts import RESEARCH_PROMPTS
        for name, template in RESEARCH_PROMPTS.items():
            assert template.version != "", f"Prompt {name} has no version"


# ===========================================================================
# Integration test — full research pipeline
# ===========================================================================
class TestResearchPipelineIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test the full research pipeline with all 8 agents."""
        # ResearchAgent calls gateway twice: once for search, once for prompt
        responses = iter([
            # Topic Analyzer
            {"expanded_topic": "AI in 2024", "category": "technology", "difficulty": "intermediate", "content_type": "educational"},
            # Research Planner
            {"strategy": "comprehensive", "sections": [{"title": "Overview", "queries": [{"query": "what is AI"}]}], "total_queries": 3},
            # Research Agent — search call (returns plain text, not JSON)
            "AI is a field of computer science.",
            # Research Agent — prompt processing
            {"facts": [{"fact": "AI is powerful", "confidence": 0.8, "category": "fact"}], "references": ["https://example.com"]},
            # Fact Verification
            {"verified_facts": [{"fact": "AI is powerful", "confidence": 0.9, "verified": True, "sources": ["src1"], "source_count": 1, "category": "fact"}], "overall_confidence": 0.9, "total_checked": 1, "total_verified": 1, "total_flagged": 0, "total_removed": 0},
            # Keyword Extraction
            {"primary_keywords": ["AI"], "secondary_keywords": ["ML"], "semantic_keywords": [], "long_tail_keywords": [], "entities": [], "concepts": [], "seo_tags": []},
            # Audience Analysis
            {"primary_persona": {"persona_name": "Tech Pro", "knowledge_level": "intermediate", "description": "Developer"}, "estimated_audience_size": "large", "engagement_drivers": []},
            # Content Angle
            {"angles": [{"angle_type": "educational", "title": "Understanding AI", "estimated_engagement": 0.8, "difficulty_to_produce": "easy"}], "selected_angle": {"angle_type": "educational", "title": "Understanding AI", "estimated_engagement": 0.8, "difficulty_to_produce": "easy"}, "selection_rationale": "Best fit"},
            # Research Summary
            {"overview": "AI overview", "important_facts": ["AI is powerful"], "key_takeaways": ["AI matters"]},
        ])

        class PipelineGateway:
            async def generate(self, prompt, **kwargs):
                resp = next(responses)
                class Result:
                    success = True
                    output = resp if isinstance(resp, str) else json.dumps(resp)
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
        state = WorkflowState()
        state.topic.raw_topic = "AI"
        state.project.name = "AI"

        agents = [
            TopicAnalyzerAgent(),
            ResearchPlannerAgent(),
            ResearchAgent(),
            FactVerificationAgent(),
            KeywordExtractionAgent(),
            AudienceAnalysisAgent(),
            ContentAngleAgent(),
            ResearchSummaryAgent(),
        ]

        for agent in agents:
            agent.enable_quality_check = False
            agent.enable_artifact_creation = False

        ctx = AgentContext(
            state=state,
            agent_name="pipeline",
            agent_type="research",
            gateways={"llm": gateway},
            identity=IdentityContext(workflow_id="test", execution_id=uuid4()),
        )

        for agent in agents:
            result = await agent.run_agent(ctx)
            assert result.success is True, f"Agent {agent.name} failed: {result.error}"

        # Verify final research package
        package_data = ctx.state.research.metadata.get("research_package")
        assert package_data is not None
        assert package_data["topic_analysis"]["expanded_topic"] == "AI in 2024"
        assert package_data["confidence_score"] == 0.9
        assert package_data["summary"]["overview"] == "AI overview"
