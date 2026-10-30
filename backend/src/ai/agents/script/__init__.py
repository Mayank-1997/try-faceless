"""Script generation subsystem — transforms Research Package into production-quality scripts.

Phase 7: Implements the complete script generation workflow with 8 agents:
- NarrativeStrategyAgent
- ScriptOutlineAgent
- HookGeneratorAgent
- SectionWriterAgent
- TransitionAgent
- CallToActionAgent
- ScriptReviewAgent
- ScriptOptimizationAgent

All agents inherit from ``BaseAgent`` and produce a structured
``ScriptPackage`` consumed by downstream agents (Storyboard, Scene Planner).
"""

from src.ai.agents.script.call_to_action import CallToActionAgent
from src.ai.agents.script.events import ScriptEventEmitter, ScriptEvents
from src.ai.agents.script.hook_generator import HookGeneratorAgent
from src.ai.agents.script.narrative_strategy import NarrativeStrategyAgent
from src.ai.agents.script.script_optimization import ScriptOptimizationAgent
from src.ai.agents.script.script_outline import ScriptOutlineAgent
from src.ai.agents.script.script_review import ScriptReviewAgent
from src.ai.agents.script.section_writer import SectionWriterAgent
from src.ai.agents.script.transition import TransitionAgent
from src.ai.agents.script.workflow import ScriptWorkflowGraph
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
