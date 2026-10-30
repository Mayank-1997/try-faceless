# Phase 6 — Topic Discovery & Research System Architecture

## Overview

The Topic Discovery & Research System transforms a simple user idea into a structured `ResearchPackage` that downstream agents (Script, Story Planner, Scene Planner) can consume. The system consists of 8 AI agents chained sequentially in a LangGraph workflow.

## Research Workflow Diagram

```
User Topic
    │
    ▼
┌──────────────────┐
│ Topic Analyzer   │  Analyzes topic: category, difficulty, content type,
│ Agent            │  longevity, research depth, missing information
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Research Planner │  Creates research plan: sections, search queries,
│ Agent            │  source diversity, fact requirements
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Research Agent   │  Gathers facts, statistics, examples, historical
│ (Web Search)     │  events, definitions from web search or LLM
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Fact Verification│  Cross-checks facts, removes conflicts, flags
│ Agent            │  uncertain claims, assigns confidence scores
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Keyword          │  Extracts primary, secondary, semantic, long-tail
│ Extraction Agent │  keywords, entities, concepts, SEO tags
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Audience         │  Identifies audience personas, knowledge level,
│ Analysis Agent   │  pain points, questions, reading level
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Content Angle    │  Generates 5+ content angles (educational, story,
│ Agent            │  comparison, timeline, etc.), selects best
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Research Summary │  Generates structured summary, assembles final
│ Agent            │  ResearchPackage with all data
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Research Package │  Final output: topic analysis, verified facts,
│                  │  keywords, audience, content angle, summary
└──────────────────┘
```

## Agent Interaction Diagram

```
                    WorkflowState
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    ▼                    ▼                    ▼
┌─────────┐      ┌───────────┐      ┌──────────────┐
│ topic_  │      │ research_ │      │ research_    │
│ analysis│      │ plan      │      │ metadata     │
│         │      │           │      │              │
└────┬────┘      └─────┬─────┘      └──────┬───────┘
     │                 │                   │
     ▼                 ▼                   ▼
  TopicAnalyzer    ResearchPlanner    ResearchAgent
  reads topic      reads topic_       reads research_plan
  writes topic_    analysis           executes web search
  analysis         writes research_   writes web_research
                                       │
                                       ▼
                                 FactVerification
                                 reads web_research
                                 writes fact_verification
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              KeywordExtraction  AudienceAnalysis  ContentAngle
              reads fact_verif   reads topic_       reads topic_
              writes keywords    analysis           analysis
                                 writes audience    reads audience
                                                    writes content_angle
                                       │
                                       ▼
                                 ResearchSummary
                                 reads ALL metadata
                                 writes research_summary
                                 assembles ResearchPackage
```

## Research Package Schema

```json
{
  "id": "UUID",
  "topic_analysis": {
    "raw_topic": "AI",
    "expanded_topic": "Artificial Intelligence in 2024",
    "category": "technology",
    "subcategory": "software engineering",
    "difficulty": "intermediate",
    "content_type": "educational",
    "longevity": "evergreen",
    "target_duration_seconds": 600,
    "research_depth": "deep",
    "user_intent": "Learn about AI tools",
    "missing_information": ["latest tools", "pricing"],
    "suggested_angles": ["comparison", "tutorial"],
    "language": "en"
  },
  "research_plan": {
    "strategy": "Multi-source research",
    "sections": [
      {
        "title": "Overview",
        "description": "General overview",
        "priority": 1,
        "queries": [
          {"query": "what is AI", "priority": 1, "source_types": ["web"]}
        ],
        "fact_requirements": ["definition", "history"]
      }
    ],
    "total_queries": 10,
    "source_diversity_required": true,
    "min_sources": 3,
    "max_sources": 10
  },
  "web_research": {
    "query": "AI",
    "facts": [{"fact": "...", "category": "fact", "confidence": 0.8}],
    "statistics": [{"fact": "...", "category": "statistic", "confidence": 0.9}],
    "examples": [{"fact": "...", "category": "example", "confidence": 0.7}],
    "historical_events": [{"fact": "...", "category": "historical_event"}],
    "definitions": [{"fact": "...", "category": "definition"}],
    "references": ["https://..."]
  },
  "fact_verification": {
    "verified_facts": [
      {"fact": "...", "confidence": 0.9, "verified": true, "sources": ["url1", "url2"]}
    ],
    "flagged_facts": [
      {"fact": "...", "confidence": 0.3, "verified": false, "conflicting": true}
    ],
    "removed_facts": ["unverifiable claim"],
    "overall_confidence": 0.85,
    "total_checked": 10,
    "total_verified": 8
  },
  "keywords": {
    "primary_keywords": ["AI", "machine learning"],
    "secondary_keywords": ["neural networks", "deep learning"],
    "semantic_keywords": ["automation", "intelligence"],
    "long_tail_keywords": ["how does AI work", "types of ML"],
    "entities": ["OpenAI", "Google", "DeepMind"],
    "concepts": ["intelligence", "learning"],
    "seo_tags": ["AI", "ML"]
  },
  "audience": {
    "primary_persona": {
      "persona_name": "Tech Professional",
      "knowledge_level": "intermediate",
      "age_range": "25-40",
      "interests": ["AI", "programming"],
      "pain_points": ["keeping up with AI"],
      "questions": ["How can I use AI?"],
      "reading_level": "advanced"
    },
    "secondary_personas": [],
    "estimated_audience_size": "large",
    "engagement_drivers": ["practical examples"]
  },
  "content_angle": {
    "angles": [
      {"angle_type": "educational", "title": "...", "estimated_engagement": 0.85},
      {"angle_type": "storytelling", "title": "...", "estimated_engagement": 0.75}
    ],
    "selected_angle": {
      "angle_type": "educational",
      "title": "Understanding AI",
      "estimated_engagement": 0.85,
      "difficulty_to_produce": "easy"
    },
    "selection_rationale": "Best engagement-to-difficulty ratio"
  },
  "summary": {
    "overview": "AI is a broad field...",
    "important_facts": ["AI coined in 1956", "ML is subset of AI"],
    "timeline": ["1956: AI coined", "2010s: Deep learning boom"],
    "examples": ["Siri", "ChatGPT"],
    "statistics": ["AI market: $100B"],
    "warnings": ["AI bias is a concern"],
    "references": ["https://..."],
    "suggested_narrative": "Start with history, then applications",
    "key_takeaways": ["AI is transformative"]
  },
  "confidence_score": 0.85,
  "created_at": "2024-01-01T00:00:00Z",
  "version": 1
}
```

## Key Components

### Research Schema (`src/ai/agents/research/schema.py`)

All Pydantic v2 models:
- `TopicAnalysis` — Structured topic analysis
- `ResearchPlan`, `ResearchSection`, `SearchQuery` — Research planning
- `ResearchFact`, `ResearchItem`, `WebResearchResult` — Web research data
- `VerifiedFact`, `FactVerificationResult` — Fact verification
- `KeywordSet` — Extracted keywords
- `AudiencePersona`, `AudienceAnalysisResult` — Audience analysis
- `ContentAngle`, `ContentAngleResult` — Content angle selection
- `ResearchSummary` — Structured summary
- `ResearchPackage` — Final output combining all results

### Research Prompts (`src/ai/agents/research/prompts.py`)

8 versioned prompt templates:
- `TOPIC_ANALYZER_PROMPT` — Topic analysis with JSON output
- `RESEARCH_PLANNER_PROMPT` — Research plan with sections and queries
- `RESEARCH_PROMPT` — Web search result processing
- `FACT_VERIFICATION_PROMPT` — Fact cross-checking
- `KEYWORD_EXTRACTION_PROMPT` — SEO keyword extraction
- `AUDIENCE_ANALYSIS_PROMPT` — Audience persona identification
- `CONTENT_ANGLE_PROMPT` — Content angle generation and selection
- `RESEARCH_SUMMARY_PROMPT` — Structured summary generation

### Research Events (`src/ai/agents/research/events.py`)

9 research-specific events extending the agent event framework:
- `ResearchStarted` — Workflow begins
- `TopicAnalyzed` — Topic analysis complete
- `ResearchPlanned` — Research plan created
- `ResearchCompleted` — Web research done
- `FactVerified` — Facts cross-checked
- `KeywordsGenerated` — Keywords extracted
- `AudienceIdentified` — Audience analyzed
- `ContentAngleSelected` — Angle selected
- `ResearchPackageCreated` — Final package assembled

### Research Workflow Graph (`src/ai/agents/research/workflow.py`)

`ResearchWorkflowGraph` extends `BaseWorkflowGraph`:
- 8 nodes (one per agent)
- 7 sequential edges
- Entry: `topic_analyzer`
- Exit: `research_summary`

## State Management

All agent outputs are persisted into `WorkflowState.research.metadata`:
- `metadata["topic_analysis"]` — TopicAnalysis dict
- `metadata["research_plan"]` — ResearchPlan dict
- `metadata["web_research"]` — WebResearchResult dict
- `metadata["fact_verification"]` — FactVerificationResult dict
- `metadata["keywords"]` — KeywordSet dict
- `metadata["audience"]` — AudienceAnalysisResult dict
- `metadata["content_angle"]` — ContentAngleResult dict
- `metadata["research_summary"]` — ResearchSummary dict
- `metadata["research_package"]` — Final ResearchPackage dict

The `ResearchData` model in `WorkflowState` was extended with a `metadata` field to store these structured outputs.

## Testing

63 unit tests in `tests/unit/test_research_agents.py`:
- Schema tests (all Pydantic models)
- Agent tests (each of the 8 agents)
- Workflow graph tests (node registration, edges, chain)
- Event tests (all 9 research events)
- Prompt template tests (all 8 templates)
- Full pipeline integration test (all 8 agents in sequence)
