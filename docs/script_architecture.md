# Phase 7 — Script Generation System Architecture

## Overview

The Script Generation System transforms a `ResearchPackage` into a production-quality YouTube script. The system consists of 8 AI agents chained sequentially in a LangGraph workflow. The output is a structured `ScriptPackage` that downstream agents (Storyboard, Scene Planner) can consume.

## Script Workflow Diagram

```
Research Package
    │
    ▼
┌──────────────────┐
│ Narrative        │  Chooses storytelling style, flow, pacing, tone
│ Strategy Agent   │  based on audience, topic, duration, content type
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Script Outline   │  Generates complete outline with sections,
│ Agent            │  subsections, talking points, timing, word counts
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Hook Generator   │  Generates 6+ hooks (question, bold statement,
│ Agent            │  unexpected fact, story, contradiction, curiosity gap)
│                  │  Selects best hook, stores rejected hooks
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Section Writer   │  Writes each section independently with narration,
│ Agent            │  facts, examples, emotional pacing, references
│ (Parallel)       │  Supports parallel execution
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Transition Agent │  Generates smooth transitions between sections,
│                  │  ensures natural flow, assigns smoothness score
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ CTA Agent        │  Generates CTAs (subscribe, like, comment, etc.),
│                  │  selects primary and secondary, matches channel style
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Script Review    │  Validates logic, flow, completeness, consistency,
│ Agent            │  fact usage, audience alignment, length, reading level
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Script           │  Improves retention, clarity, redundancy, sentence
│ Optimization     │  variety, natural speech, engagement
│ Agent            │  Assembles final ScriptPackage
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Script Package   │  Final output: narrative strategy, outline, hook,
│                  │  sections, transitions, CTA, review, optimization
└──────────────────┘
```

## Agent Interaction Diagram

```
                    WorkflowState
                    ├── research.metadata["research_package"]
                    └── script.metadata
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    ▼                    ▼                    ▼
┌─────────┐      ┌───────────┐      ┌──────────────┐
│narrative│      │ script_   │      │ hook_result  │
│_strategy│      │ outline   │      │              │
└────┬────┘      └─────┬─────┘      └──────┬───────┘
     │                 │                   │
     ▼                 ▼                   ▼
  NarrativeStrategy  ScriptOutline      HookGenerator
  reads research     reads narrative_   reads narrative_
  package            strategy           strategy
  writes narrative_  writes script_     writes hook_result
  strategy           outline            selects best hook
                         │
                         ▼
                    SectionWriter
                    reads script_outline
                    writes sections[]
                    (one per outline section)
                         │
                    ┌────┴────┐
                    ▼         ▼
              Transition    CTA
              reads sections reads narrative_
              writes transitions strategy
              updates sections writes cta_result
                    │         │
                    └────┬────┘
                         ▼
                    ScriptReview
                    reads ALL sections
                    reads hook_result
                    writes review
                         │
                         ▼
                    ScriptOptimization
                    reads ALL metadata
                    writes optimization
                    assembles ScriptPackage
```

## Script Package Schema

```json
{
  "id": "UUID",
  "narrative_strategy": {
    "style": "educational",
    "rationale": "Best for topic",
    "flow": "Start simple, go deep",
    "pacing": "moderate",
    "tone": "informative",
    "emotional_arc": "Curiosity to understanding",
    "key_beats": ["Hook", "Explain", "Conclude"],
    "audience_alignment": "Matches tech professionals"
  },
  "outline": {
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
        "importance": "high"
      }
    ],
    "closing": "Closing description",
    "total_estimated_time_seconds": 600,
    "total_target_word_count": 1500
  },
  "hook_result": {
    "hooks": [
      {"hook_type": "question", "content": "What is AI?", "estimated_retention_score": 0.85},
      {"hook_type": "curiosity_gap", "content": "The truth about AI...", "estimated_retention_score": 0.9}
    ],
    "selected_hook": {
      "hook_type": "curiosity_gap",
      "content": "The truth about AI...",
      "estimated_retention_score": 0.9
    },
    "rejected_hooks": [...]
  },
  "sections": [
    {
      "section_id": "s1",
      "title": "Introduction",
      "narration": "Welcome to this video about AI...",
      "estimated_duration_seconds": 60,
      "word_count": 150,
      "emotion": "excited",
      "importance": "high",
      "purpose": "inform",
      "references": ["ref1"],
      "facts_used": ["AI was coined in 1956"],
      "examples": ["Siri"],
      "future_scene_count": 3,
      "transition": "Now let's dive deeper..."
    }
  ],
  "transitions": {
    "transitions": {"s1": "Now let's dive deeper..."},
    "flow_analysis": "Sections flow naturally",
    "smoothness_score": 0.85
  },
  "cta_result": {
    "ctas": [{"cta_type": "subscribe", "content": "Subscribe!"}],
    "primary_cta": {"cta_type": "subscribe", "content": "Subscribe!"},
    "secondary_ctas": [{"cta_type": "like", "content": "Like!"}]
  },
  "review": {
    "logic_score": 0.85,
    "flow_score": 0.8,
    "completeness_score": 0.9,
    "overall_score": 0.84,
    "issues": [],
    "strengths": ["Good flow"],
    "passed": true
  },
  "optimization": {
    "optimized_content": "Optimized script text...",
    "retention_improvement": 0.15,
    "engagement_score": 0.88,
    "changes_made": ["Improved hook", "Reduced repetition"]
  },
  "quality": {
    "retention_potential": 0.88,
    "curiosity": 0.67,
    "flow": 0.8,
    "clarity": 0.6,
    "natural_speech": 0.9,
    "fact_density": 0.8,
    "audience_alignment": 0.9,
    "overall_score": 0.84
  },
  "full_script": "Complete assembled script text",
  "title": "Understanding AI",
  "word_count": 1500,
  "estimated_duration_seconds": 600,
  "reading_time_minutes": 10.0,
  "references": ["ref1", "ref2"],
  "version": 1,
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Script Section Structure

Each section contains:
- **Section ID**: Unique identifier (s1, s2, etc.)
- **Title**: Section title
- **Narration**: Full spoken text for the section
- **Estimated Duration**: In seconds
- **Word Count**: Actual word count of narration
- **Emotion**: Emotional tone (excited, serious, curious, empathetic, dramatic, neutral)
- **Importance**: Priority level (low, medium, high, critical)
- **Purpose**: Content purpose (inform, persuade, entertain, illustrate, transition)
- **References**: Source references used
- **Transition**: Transition text to next section
- **Facts Used**: Facts referenced in this section
- **Examples**: Examples used
- **Future Scene Count**: Estimated number of visual scenes needed

## Key Components

### Script Schema (`src/ai/agents/script/schema.py`)

All Pydantic v2 models:
- `NarrativeStrategy` — Storytelling approach
- `OutlineSection`, `ScriptOutline` — Script outline structure
- `Hook`, `HookResult` — Hook generation and selection
- `ScriptSection` — Fully written section with metadata
- `TransitionResult` — Smooth transitions between sections
- `CallToAction`, `CTAResult` — CTA generation
- `ScriptReviewResult` — Quality review scores
- `ScriptOptimizationResult` — Optimization results
- `ScriptQualityEvaluation` — Quality evaluation dimensions
- `ScriptPackage` — Final output combining all results

### Script Prompts (`src/ai/agents/script/prompts.py`)

8 versioned prompt templates:
- `NARRATIVE_STRATEGY_PROMPT` — Strategy selection
- `SCRIPT_OUTLINE_PROMPT` — Outline generation
- `HOOK_GENERATOR_PROMPT` — Hook generation
- `SECTION_WRITER_PROMPT` — Section writing
- `TRANSITION_PROMPT` — Transition generation
- `CTA_PROMPT` — CTA generation
- `SCRIPT_REVIEW_PROMPT` — Script review
- `SCRIPT_OPTIMIZATION_PROMPT` — Script optimization

### Script Events (`src/ai/agents/script/events.py`)

10 script-specific events:
- `ScriptStarted` — Workflow begins
- `NarrativeStrategySelected` — Strategy chosen
- `OutlineGenerated` — Outline created
- `HookSelected` — Best hook selected
- `SectionsGenerated` — All sections written
- `TransitionsGenerated` — Transitions created
- `CTAGenerated` — CTAs generated
- `ScriptReviewed` — Review completed
- `ScriptOptimized` — Optimization done
- `ScriptCompleted` — Package assembled

### Script Workflow Graph (`src/ai/agents/script/workflow.py`)

`ScriptWorkflowGraph` extends `BaseWorkflowGraph`:
- 8 nodes (one per agent)
- 7 sequential edges
- Entry: `narrative_strategy`
- Exit: `script_optimization`

## State Management

All agent outputs are persisted into `WorkflowState.script.metadata`:
- `metadata["narrative_strategy"]` — NarrativeStrategy dict
- `metadata["script_outline"]` — ScriptOutline dict
- `metadata["hook_result"]` — HookResult dict
- `metadata["sections"]` — List of ScriptSection dicts
- `metadata["transitions"]` — TransitionResult dict
- `metadata["cta_result"]` — CTAResult dict
- `metadata["review"]` — ScriptReviewResult dict
- `metadata["optimization"]` — ScriptOptimizationResult dict
- `metadata["script_package"]` — Final ScriptPackage dict

The `ScriptData` model in `WorkflowState` was extended with a `metadata` field to store these structured outputs.

## Quality Evaluation

The script is evaluated on multiple dimensions:
- **Retention Potential**: How likely viewers are to keep watching
- **Curiosity**: How much curiosity the script generates
- **Flow**: How smoothly sections connect
- **Clarity**: How clear and understandable the content is
- **Natural Speech**: How natural the narration sounds when spoken
- **Fact Density**: How well facts are integrated
- **Audience Alignment**: How well it matches the target audience
- **Overall Score**: Weighted combination of all dimensions

## Validation

Scripts are rejected if they:
- Are too short (below minimum word count)
- Miss required sections
- Contain unsupported claims
- Have poor transitions
- Lack narrative flow

## Testing

64 unit tests in `tests/unit/test_script_agents.py`:
- Schema tests (all Pydantic models)
- Agent tests (each of the 8 agents)
- Workflow graph tests (node registration, edges, chain)
- Event tests (all 10 script events)
- Prompt template tests (all 8 templates)
- Full pipeline integration test (all 8 agents in sequence)
