"""Research subsystem — Topic Discovery & Research agents.

Phase 6: Implements the complete research workflow with 8 agents:
- TopicAnalyzerAgent
- ResearchPlannerAgent
- ResearchAgent
- FactVerificationAgent
- KeywordExtractionAgent
- AudienceAnalysisAgent
- ContentAngleAgent
- ResearchSummaryAgent

All agents inherit from ``BaseAgent`` and produce a structured
``ResearchPackage`` consumed by downstream agents.
"""

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
    ResearchItem,
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
