"""Prompt templates for research agents.

Each agent has its own prompt template with versioning, variables,
and structured JSON output expectations.  Templates are defined
programmatically via ``PromptTemplate.from_string()``.
"""

from __future__ import annotations

from src.ai.agents.prompt_template import PromptTemplate


# ---------------------------------------------------------------------------
# Topic Analyzer prompt
# ---------------------------------------------------------------------------
TOPIC_ANALYZER_PROMPT = PromptTemplate.from_string(
    "topic_analyzer",
    """You are a topic analysis expert. Analyze the following topic and provide a structured analysis.

Topic: {{topic}}
Requested Video Duration: {{target_duration}} seconds (fixed by the user — treat it as a hard constraint for all downstream planning)

Respond with a JSON object containing:
{
  "expanded_topic": "A more detailed and specific version of the topic",
  "category": "Main category (e.g. technology, science, business, health, education, entertainment, lifestyle, finance)",
  "subcategory": "More specific subcategory",
  "difficulty": "beginner | intermediate | advanced | expert",
  "content_type": "educational | entertainment | mixed",
  "longevity": "evergreen | trending | seasonal",
  "target_duration_seconds": 600,
  "research_depth": "light | standard | deep | comprehensive",
  "user_intent": "What the user wants to achieve with this content",
  "missing_information": ["List of information gaps that need research"],
  "suggested_angles": ["List of possible content angles"],
  "language": "en"
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Analyzes a user topic and produces structured topic analysis",
)


# ---------------------------------------------------------------------------
# Research Planner prompt
# ---------------------------------------------------------------------------
RESEARCH_PLANNER_PROMPT = PromptTemplate.from_string(
    "research_planner",
    """You are a research planning expert. Create a comprehensive research plan for the following topic.

Topic: {{topic}}
Category: {{category}}
Research Depth: {{research_depth}}

Respond with a JSON object containing:
{
  "strategy": "Overall research strategy description",
  "sections": [
    {
      "title": "Section title",
      "description": "What this section covers",
      "priority": 1,
      "queries": [
        {"query": "search query string", "priority": 1, "source_types": ["web", "academic", "news"], "expected_results": "What we expect to find"}
      ],
      "fact_requirements": ["Specific facts needed"]
    }
  ],
  "total_queries": 10,
  "source_diversity_required": true,
  "min_sources": 3,
  "max_sources": 10,
  "language": "en"
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Creates a structured research plan with sections and search queries",
)


# ---------------------------------------------------------------------------
# Research Agent prompt (web search result processing)
# ---------------------------------------------------------------------------
RESEARCH_PROMPT = PromptTemplate.from_string(
    "research_agent",
    """You are a research analyst. Analyze the following search results and extract structured information.

Topic: {{topic}}
Search Query: {{query}}

Search Results:
{{search_results}}

Respond with a JSON object containing:
{
  "facts": [
    {"fact": "The fact statement", "source_url": "URL", "source_title": "Title", "category": "fact", "confidence": 0.8}
  ],
  "statistics": [
    {"fact": "Statistic with numbers", "source_url": "URL", "source_title": "Title", "category": "statistic", "confidence": 0.9}
  ],
  "examples": [
    {"fact": "Real-world example", "source_url": "URL", "source_title": "Title", "category": "example", "confidence": 0.7}
  ],
  "historical_events": [
    {"fact": "Historical event with date", "source_url": "URL", "source_title": "Title", "category": "historical_event", "confidence": 0.8}
  ],
  "definitions": [
    {"fact": "Term definition", "source_url": "URL", "source_title": "Title", "category": "definition", "confidence": 0.9}
  ],
  "references": ["List of source URLs"]
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Processes web search results and extracts structured facts",
)


# ---------------------------------------------------------------------------
# Fact Verification prompt
# ---------------------------------------------------------------------------
FACT_VERIFICATION_PROMPT = PromptTemplate.from_string(
    "fact_verification",
    """You are a fact-checking expert. Cross-verify the following facts and assess their accuracy.

Topic: {{topic}}

Facts to verify:
{{facts}}

Respond with a JSON object containing:
{
  "verified_facts": [
    {
      "fact": "The fact statement",
      "confidence": 0.9,
      "verified": true,
      "conflicting": false,
      "sources": ["source1", "source2"],
      "source_count": 2,
      "notes": "Verification notes",
      "category": "fact"
    }
  ],
  "flagged_facts": [
    {
      "fact": "Uncertain fact",
      "confidence": 0.4,
      "verified": false,
      "conflicting": true,
      "sources": ["source1"],
      "source_count": 1,
      "notes": "Why this is flagged",
      "category": "fact"
    }
  ],
  "removed_facts": ["Facts that are clearly wrong or unverifiable"],
  "overall_confidence": 0.75,
  "total_checked": 10,
  "total_verified": 7,
  "total_flagged": 2,
  "total_removed": 1
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Cross-checks facts and assigns confidence scores",
)


# ---------------------------------------------------------------------------
# Keyword Extraction prompt
# ---------------------------------------------------------------------------
KEYWORD_EXTRACTION_PROMPT = PromptTemplate.from_string(
    "keyword_extraction",
    """You are an SEO and keyword expert. Extract keywords from the following research content.

Topic: {{topic}}

Research Summary:
{{research_summary}}

Respond with a JSON object containing:
{
  "primary_keywords": ["3-5 most important keywords"],
  "secondary_keywords": ["5-10 supporting keywords"],
  "semantic_keywords": ["5-10 semantically related keywords"],
  "long_tail_keywords": ["5-10 long-tail keyword phrases"],
  "entities": ["Named entities (people, places, organizations, products)"],
  "concepts": ["Abstract concepts and themes"],
  "seo_tags": ["Tags for SEO optimization"]
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Extracts primary, secondary, semantic, and long-tail keywords",
)


# ---------------------------------------------------------------------------
# Audience Analysis prompt
# ---------------------------------------------------------------------------
AUDIENCE_ANALYSIS_PROMPT = PromptTemplate.from_string(
    "audience_analysis",
    """You are an audience analysis expert. Identify the target audience for content about this topic.

Topic: {{topic}}
Category: {{category}}
Content Type: {{content_type}}

Respond with a JSON object containing:
{
  "primary_persona": {
    "persona_name": "Persona name",
    "description": "Detailed persona description",
    "knowledge_level": "beginner | intermediate | advanced | expert",
    "age_range": "25-35",
    "interests": ["List of interests"],
    "pain_points": ["List of pain points"],
    "questions": ["Questions this audience would ask"],
    "reading_level": "basic | standard | advanced",
    "preferred_content_style": "What style resonates with them"
  },
  "secondary_personas": [
    {
      "persona_name": "Secondary persona",
      "description": "Description",
      "knowledge_level": "intermediate",
      "age_range": "30-45",
      "interests": [],
      "pain_points": [],
      "questions": [],
      "reading_level": "standard",
      "preferred_content_style": ""
    }
  ],
  "estimated_audience_size": "large | medium | small | niche",
  "engagement_drivers": ["What drives engagement for this audience"]
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Identifies audience personas and their characteristics",
)


# ---------------------------------------------------------------------------
# Content Angle prompt
# ---------------------------------------------------------------------------
CONTENT_ANGLE_PROMPT = PromptTemplate.from_string(
    "content_angle",
    """You are a content strategy expert. Generate and select the best content angle for this topic.

Topic: {{topic}}
Category: {{category}}
Target Audience: {{audience}}
Content Type: {{content_type}}

Respond with a JSON object containing:
{
  "angles": [
    {
      "angle_type": "educational",
      "title": "Angle title",
      "description": "Detailed description",
      "rationale": "Why this angle works",
      "estimated_engagement": 0.8,
      "difficulty_to_produce": "easy | medium | hard"
    },
    {
      "angle_type": "storytelling",
      "title": "Angle title",
      "description": "Detailed description",
      "rationale": "Why this angle works",
      "estimated_engagement": 0.7,
      "difficulty_to_produce": "medium"
    }
  ],
  "selected_angle": {
    "angle_type": "educational",
    "title": "Selected angle title",
    "description": "Description",
    "rationale": "Why this was selected",
    "estimated_engagement": 0.8,
    "difficulty_to_produce": "easy"
  },
  "selection_rationale": "Detailed explanation of why this angle was selected"
}

Generate at least 5 angles covering: educational, storytelling, comparison, timeline, explainer, case_study, opinion.
Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Generates and selects the best content angle",
)


# ---------------------------------------------------------------------------
# Research Summary prompt
# ---------------------------------------------------------------------------
RESEARCH_SUMMARY_PROMPT = PromptTemplate.from_string(
    "research_summary",
    """You are a research summarization expert. Create a structured summary from the following research data.

Topic: {{topic}}

Verified Facts:
{{verified_facts}}

Statistics:
{{statistics}}

Audience:
{{audience}}

Content Angle:
{{content_angle}}

Respond with a JSON object containing:
{
  "overview": "High-level overview of the topic (2-3 paragraphs)",
  "important_facts": ["List of the most important facts"],
  "timeline": ["Chronological timeline of key events"],
  "examples": ["Real-world examples"],
  "statistics": ["Key statistics with context"],
  "warnings": ["Caveats, controversies, or things to be careful about"],
  "references": ["List of reference URLs"],
  "suggested_narrative": "Suggested narrative structure for the content",
  "key_takeaways": ["Main takeaways for the audience"]
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Generates a structured research summary",
)


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------
RESEARCH_PROMPTS = {
    "topic_analyzer": TOPIC_ANALYZER_PROMPT,
    "research_planner": RESEARCH_PLANNER_PROMPT,
    "research_agent": RESEARCH_PROMPT,
    "fact_verification": FACT_VERIFICATION_PROMPT,
    "keyword_extraction": KEYWORD_EXTRACTION_PROMPT,
    "audience_analysis": AUDIENCE_ANALYSIS_PROMPT,
    "content_angle": CONTENT_ANGLE_PROMPT,
    "research_summary": RESEARCH_SUMMARY_PROMPT,
}
"""Dictionary of all research prompt templates indexed by name."""
