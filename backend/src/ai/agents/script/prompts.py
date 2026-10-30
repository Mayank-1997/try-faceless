"""Prompt templates for script generation agents.

Each agent has its own prompt template with versioning, variables,
and structured JSON output expectations.  Templates are defined
programmatically via ``PromptTemplate.from_string()``.
"""

from __future__ import annotations

from src.ai.agents.prompt_template import PromptTemplate

# ---------------------------------------------------------------------------
# Narrative Strategy prompt
# ---------------------------------------------------------------------------
NARRATIVE_STRATEGY_PROMPT = PromptTemplate.from_string(
    "narrative_strategy",
    """You are a narrative strategy expert. Choose the best storytelling approach for a YouTube script.

Topic: {{topic}}
Category: {{category}}
Content Type: {{content_type}}
Target Duration: {{target_duration}} seconds
Audience: {{audience}}
Content Angle: {{content_angle}}

Research Summary:
{{research_summary}}

Respond with a JSON object containing:
{
  "style": "educational | storytelling | documentary | mystery | timeline | case_study | comparison | tutorial | problem_solution",
  "rationale": "Why this style was chosen",
  "flow": "Description of the narrative flow from start to finish",
  "pacing": "fast | moderate | slow | varied",
  "tone": "informative | casual | dramatic | humorous | inspirational",
  "emotional_arc": "Description of emotional journey",
  "key_beats": ["List of key narrative beats"],
  "audience_alignment": "How this strategy aligns with the audience"
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Chooses the best narrative strategy for the script",
)


# ---------------------------------------------------------------------------
# Script Outline prompt
# ---------------------------------------------------------------------------
SCRIPT_OUTLINE_PROMPT = PromptTemplate.from_string(
    "script_outline",
    """You are a script outline expert. Create a complete script outline for a YouTube video.

Topic: {{topic}}
Narrative Style: {{narrative_style}}
Target Duration: {{target_duration}} seconds
Target Word Count: {{target_word_count}}

Research Summary:
{{research_summary}}

Key Facts:
{{key_facts}}

Duration budget — HARD constraints, not suggestions:
- YOU decide how many sections the story needs to tell a COMPLETE story in exactly {{target_duration}} seconds (e.g. hook/context, main beats, conflict/climax, resolution — adapt to the narrative style). Do not produce more content than the budget allows — size the story to the time.
- Each section's "estimated_time_seconds" must be an EVEN number of seconds >= 4 (each scene is produced from 4/6/8-second generated video clips, e.g. a 12s section is rendered as 8s + 4s).
- The sum of all "estimated_time_seconds" MUST equal exactly {{target_duration}}.
- Each section's "target_word_count" must be about 2.5 words per second of its allotted time (≈150 wpm narration), and "total_target_word_count" MUST equal {{target_word_count}}.

Respond with a JSON object containing:
{
  "title": "Script title",
  "opening": "Opening description",
  "sections": [
    {
      "section_id": "s1",
      "title": "Section title",
      "description": "What this section covers",
      "key_talking_points": ["Point 1", "Point 2"],
      "estimated_time_seconds": 12,
      "target_word_count": 30,
      "references": ["ref1"],
      "subsections": ["Sub 1", "Sub 2"],
      "importance": "high"
    }
  ],
  "closing": "Closing description",
  "total_estimated_time_seconds": {{target_duration}},
  "total_target_word_count": {{target_word_count}},
  "references": ["ref1", "ref2"]
}

Provide only the JSON object, no additional text.""",
    version="2.0.0",
    description="Creates a complete script outline with sections and timing sized to the target duration",
)


# ---------------------------------------------------------------------------
# Hook Generator prompt
# ---------------------------------------------------------------------------
HOOK_GENERATOR_PROMPT = PromptTemplate.from_string(
    "hook_generator",
    """You are a hook writing expert. Generate multiple hooks for a YouTube video.

Topic: {{topic}}
Narrative Style: {{narrative_style}}
Audience: {{audience}}
Content Angle: {{content_angle}}

Research Summary:
{{research_summary}}

Generate hooks using these types: question, bold_statement, unexpected_fact, story, contradiction, curiosity_gap

Respond with a JSON object containing:
{
  "hooks": [
    {
      "hook_type": "question",
      "content": "The hook text",
      "rationale": "Why this hook works",
      "estimated_retention_score": 0.85
    }
  ]
}

Generate at least 6 hooks covering all types.
Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Generates multiple hooks and selects the best one",
)


# ---------------------------------------------------------------------------
# Section Writer prompt
# ---------------------------------------------------------------------------
SECTION_WRITER_PROMPT = PromptTemplate.from_string(
    "section_writer",
    """You are a professional script writer.
Write the complete narration for every section of a YouTube video.

Topic: {{topic}}
Narrative Style: {{narrative_style}}
Tone: {{tone}}

Sections to write (write a narration for each):
{{sections}}

Research Facts Available:
{{research_facts}}

Respond with a JSON object containing:
{
  "sections": [
    {
      "section_id": "s1",
      "title": "Section title",
      "narration": "The full narration text for this section",
      "estimated_duration_seconds": 60,
      "word_count": 150,
      "emotion": "excited | serious | curious | empathetic | dramatic | neutral",
      "importance": "low | medium | high | critical",
      "purpose": "inform | persuade | entertain | illustrate | transition",
      "references": ["ref1"],
      "facts_used": ["Fact 1 used in this section"],
      "examples": ["Example 1 used in this section"],
      "future_scene_count": 3
    }
  ]
}

- Write natural, conversational narration suitable for spoken content.
- Return one entry for every section listed above.
- Match the target word count and estimated duration for each section — about
  2.5 spoken words per second of the section's allotted time (e.g. a 20s
  section needs ~50 words).  Do NOT write more than the section's budget.
- Do not add any extra keys outside the JSON object.
Provide only the JSON object, no additional text.""",
    version="2.0.0",
    description="Writes all complete script sections in a single call",
)


# ---------------------------------------------------------------------------
# Transition prompt
# ---------------------------------------------------------------------------
TRANSITION_PROMPT = PromptTemplate.from_string(
    "transition",
    """You are a script transition expert. Create smooth transitions between script sections.

Topic: {{topic}}
Narrative Style: {{narrative_style}}

Sections:
{{sections}}

Respond with a JSON object containing:
{
  "transitions": {
    "s1": "Transition from section 1 to section 2",
    "s2": "Transition from section 2 to section 3"
  },
  "flow_analysis": "Analysis of how sections connect",
  "smoothness_score": 0.85
}

The transitions dict keys are section_ids, values are the transition text leading to the NEXT section.
Ensure transitions are natural and avoid abrupt topic changes.
Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Generates smooth transitions between script sections",
)


# ---------------------------------------------------------------------------
# Call to Action prompt
# ---------------------------------------------------------------------------
CTA_PROMPT = PromptTemplate.from_string(
    "cta",
    """You are a call-to-action expert. Generate CTAs for a YouTube video.

Topic: {{topic}}
Audience: {{audience}}
Narrative Style: {{narrative_style}}
Channel Style: {{channel_style}}

Generate CTAs using these types: subscribe, like, comment, visit_website, download, newsletter

Respond with a JSON object containing:
{
  "ctas": [
    {
      "cta_type": "subscribe",
      "content": "CTA text",
      "placement": "end | mid | intro",
      "rationale": "Why this CTA works"
    }
  ],
  "primary_cta": {
    "cta_type": "subscribe",
    "content": "Primary CTA text",
    "placement": "end",
    "rationale": "Why this is primary"
  },
  "secondary_ctas": [
    {
      "cta_type": "like",
      "content": "Secondary CTA text",
      "placement": "end",
      "rationale": "Why this is secondary"
    }
  ],
  "channel_style_match": "How CTAs match channel style"
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Generates call-to-action content matching channel style",
)


# ---------------------------------------------------------------------------
# Script Review prompt
# ---------------------------------------------------------------------------
SCRIPT_REVIEW_PROMPT = PromptTemplate.from_string(
    "script_review",
    """You are a script review expert.
Review the following script for quality and effectiveness.

Topic: {{topic}}
Target Audience: {{audience}}
Target Duration: {{target_duration}} seconds

Full Script:
{{full_script}}

Respond with a JSON object containing:
{
  "logic_score": 0.85,
  "flow_score": 0.8,
  "completeness_score": 0.9,
  "consistency_score": 0.85,
  "fact_usage_score": 0.8,
  "audience_alignment_score": 0.9,
  "length_score": 0.75,
  "reading_level_score": 0.85,
  "overall_score": 0.84,
  "issues": ["List of identified issues"],
  "strengths": ["List of script strengths"],
  "recommendations": ["List of improvement recommendations"],
  "passed": true
}

Scores should be 0.0 to 1.0. 'passed' is true if overall_score >= 0.7 and no critical issues.
Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Reviews script for logic, flow, completeness, and quality",
)


# ---------------------------------------------------------------------------
# Script Optimization prompt
# ---------------------------------------------------------------------------
SCRIPT_OPTIMIZATION_PROMPT = PromptTemplate.from_string(
    "script_optimization",
    """You are a script optimization expert. Improve the following script for maximum retention and engagement.

Topic: {{topic}}
Audience: {{audience}}

Original Script:
{{full_script}}

Review Issues:
{{review_issues}}

Respond with a JSON object containing:
{
  "optimized_content": "The full optimized script text",
  "retention_improvement": 0.15,
  "clarity_improvement": 0.1,
  "redundancy_reduction": 0.2,
  "sentence_variety_score": 0.85,
  "natural_speech_score": 0.9,
  "engagement_score": 0.88,
  "changes_made": ["List of specific changes made"],
  "optimized_sections": [
    {
      "section_id": "s1",
      "title": "Section title",
      "narration": "Optimized narration",
      "estimated_duration_seconds": 120,
      "word_count": 300,
      "emotion": "excited",
      "importance": "high",
      "purpose": "inform",
      "references": [],
      "facts_used": [],
      "examples": [],
      "future_scene_count": 3
    }
  ]
}

Improve: retention, clarity, redundancy, sentence variety, natural speech, engagement.
Reduce repetition while preserving all facts.
Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Optimizes script for retention, clarity, and engagement",
)


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------
SCRIPT_PROMPTS = {
    "narrative_strategy": NARRATIVE_STRATEGY_PROMPT,
    "script_outline": SCRIPT_OUTLINE_PROMPT,
    "hook_generator": HOOK_GENERATOR_PROMPT,
    "section_writer": SECTION_WRITER_PROMPT,
    "transition": TRANSITION_PROMPT,
    "cta": CTA_PROMPT,
    "script_review": SCRIPT_REVIEW_PROMPT,
    "script_optimization": SCRIPT_OPTIMIZATION_PROMPT,
}
"""Dictionary of all script prompt templates indexed by name."""
