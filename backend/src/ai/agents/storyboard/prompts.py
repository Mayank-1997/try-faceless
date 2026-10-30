"""Prompt templates for storyboard & scene planning agents.

Each agent has its own prompt template with versioning, variables,
and structured JSON output expectations.  Templates are defined
programmatically via ``PromptTemplate.from_string()``.
"""

from src.ai.agents.prompt_template import PromptTemplate

STORY_ANALYZER_PROMPT = PromptTemplate.from_string(
    "story_analyzer",
    """You are a narrative analysis expert. Analyze the following script for visual storytelling opportunities.

Script Title: {{script_title}}
Narrative Style: {{narrative_style}}

Full Script:
{{full_script}}

Respond with a JSON object containing:
{
  "narrative_flow": "Description of the overall narrative flow",
  "emotional_peaks": ["List of emotional peak moments"],
  "pacing": "fast | moderate | slow | varied",
  "scene_boundaries": ["List of natural scene boundary descriptions"],
  "emphasis_points": ["List of points that need visual emphasis"],
  "dramatic_moments": ["List of dramatic moments"],
  "visual_opportunities": ["List of visual opportunities for each section"]
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Analyzes script narrative flow, emotional peaks, pacing, and visual opportunities"
)

STORY_BEAT_PROMPT = PromptTemplate.from_string(
    "story_beat",
    """You are a story structure expert. Convert the following script into story beats.

Script Title: {{script_title}}
Narrative Style: {{narrative_style}}

Full Script:
{{full_script}}

Story Analysis:
{{story_analysis}}

Convert the script into story beats using types: introduction, conflict, explanation, reveal, transition, conclusion

Respond with a JSON object containing:
{
  "beats": [
    {
      "beat_type": "introduction",
      "purpose": "What this beat accomplishes",
      "emotion": "Primary emotion",
      "duration_seconds": 30,
      "importance": "high",
      "description": "Description of this beat"
    }
  ]
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Converts script into story beats with purpose, emotion, duration, and importance"
)

SCENE_SEGMENTATION_PROMPT = PromptTemplate.from_string(
    "scene_segmentation",
    """You are a scene planning expert. Split the following script into production scenes.

Script Title: {{script_title}}
Target Duration: {{target_duration}} seconds

Full Script:
{{full_script}}

Story Beats:
{{story_beats}}

Split the script into production scenes. Each scene should be a coherent visual unit.

Duration budget - HARD constraints, not suggestions:
- YOU decide how many scenes the story needs to be told completely within {{target_duration}} seconds.
- SINGLE-CONTINUOUS-SHOT RULE: if the script describes ONE continuous physical action in ONE location (a jump, a dive, a trick, a single uninterrupted shot) AND the target duration is <= 8 seconds, output EXACTLY ONE scene covering the full {{target_duration}} seconds. Each scene boundary produces a separately generated video clip, so splitting a single continuous action creates a visible seam where the character/setting changes.
- For multi-beat or multi-location stories, prefer the FEWEST scenes that still tell the story.
- Every scene's "estimated_duration_seconds" MUST be an even number >= 4 (each scene is produced from 4/6/8-second generated video clips, e.g. a 12s scene renders as 8s + 4s).
- The sum of all estimated_duration_seconds MUST equal exactly {{target_duration}}.
- Each scene's narration must fit its duration: ~2.5 spoken words per second.

Scene types: talking, diagram, animation, timeline, infographic, comparison, map, screenshot, code, product_demo, stock_footage, ai_image, ai_video, mixed

Respond with a JSON object containing:
{
  "scenes": [
    {
      "scene_number": 1,
      "scene_id": "sc1",
      "title": "Scene title",
      "start_timestamp": 0.0,
      "end_timestamp": 30.0,
      "narration": "The narration text for this scene",
      "estimated_duration_seconds": 30,
      "scene_goal": "What this scene should achieve visually",
      "scene_type": "talking"
    }
  ]
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Splits script into production scenes with timing, goals, and types"
)

VISUAL_STORYBOARD_PROMPT = PromptTemplate.from_string(
    "visual_storyboard",
    """You are a visual storyboard expert. Create detailed visual descriptions for each scene.

Topic: {{topic}}
Narrative Style: {{narrative_style}}
Visual Style: {{visual_style}}

Scenes:
{{scenes}}

For every scene generate a visual description including composition, foreground, background, objects, characters, environment, mood, lighting, color palette, depth, and visual style.

CRITICAL - visual continuity: each scene is generated as an INDEPENDENT video clip. For the final video to look like one continuous film rather than unrelated clips stitched together:

1. First produce "shared_context": one canonical paragraph (2-3 sentences) describing THE SAME protagonist (exact gender, age range, hair, clothing, distinctive features) and THE SAME setting (specific location, terrain, time of day, lighting, weather). Reuse the EXACT same wording in every scene - never rephrase it per scene.

2. If the story happens in one location/time, every scene's environment, background, lighting, color_palette, and visual_style MUST describe that same place with the same details - do NOT invent a different landscape (e.g. canyon vs. alpine lake) or a different-looking person per scene.

3. In each scene's "characters" field, repeat the protagonist's full identifying description from shared_context verbatim - not just "the athlete" or "the woman".

Respond with a JSON object containing:
{
  "shared_context": "One canonical paragraph describing the protagonist's exact appearance and the shared setting/location/lighting — identical wording used in every scene.",
  "visual_plans": [
    {
      "scene_id": "sc1",
      "visual_description": "Detailed visual description",
      "composition": "Rule of thirds, centered, etc.",
      "foreground": "Foreground elements",
      "background": "Background elements",
      "objects": ["Object 1", "Object 2"],
      "characters": ["Character 1"],
      "environment": "Environment description",
      "mood": "Mood description",
      "lighting": "Lighting description",
      "color_palette": ["#FF0000", "#00FF00"],
      "depth": "flat | shallow | deep",
      "visual_style": "Style description"
    }
  ]
}

Provide only the JSON object, no additional text.""",
    version="1.1.0",
    description="Generates detailed visual descriptions for each scene plus a shared character/setting bible for cross-clip continuity"
)

CAMERA_PLANNER_PROMPT = PromptTemplate.from_string(
    "camera_planner",
    """You are a camera planning expert. Plan camera angles and movements for each scene.

Topic: {{topic}}

Scenes:
{{scenes}}

Visual Plans:
{{visual_plans}}

For each scene determine: camera angle, camera distance, lens, movement, motion speed, and focus point.

Camera angles: wide, medium, close_up, extreme_close_up, overhead, low_angle, high_angle, dutch, pov
Camera movements: static, pan_left, pan_right, zoom_in, zoom_out, tilt_up, tilt_down, dolly_in, dolly_out, tracking, orbit

Respond with a JSON object containing:
{
  "camera_plans": [
    {
      "scene_id": "sc1",
      "camera_angle": "medium",
      "camera_distance": "medium",
      "lens": "standard",
      "movement": "static",
      "motion_speed": "normal",
      "focus_point": "Center of frame"
    }
  ]
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Plans camera angles, distances, lenses, and movements for each scene"
)

ANIMATION_PLANNER_PROMPT = PromptTemplate.from_string(
    "animation_planner",
    """You are an animation planning expert. Plan animations for each scene.

Topic: {{topic}}

Scenes:
{{scenes}}

Visual Plans:
{{visual_plans}}

Camera Plans:
{{camera_plans}}

For each scene plan: element animation, text animation, camera motion, object motion, background motion, timing, entrance/exit transitions, and scene effects.

Respond with a JSON object containing:
{
  "animation_plans": [
    {
      "scene_id": "sc1",
      "element_animation": "Description of element animations",
      "text_animation": "Text animation description",
      "camera_motion": "Camera motion description",
      "object_motion": "Object motion description",
      "background_motion": "Background motion description",
      "timing": "Timing description",
      "entrance_transition": "Fade in",
      "exit_transition": "Fade out",
      "scene_effects": ["Effect 1", "Effect 2"]
    }
  ]
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Plans element, text, camera, and object animations for each scene"
)

ASSET_DECISION_PROMPT = PromptTemplate.from_string(
    "asset_decision",
    """You are an asset planning expert. Decide the best asset type for each scene.

Topic: {{topic}}

Scenes:
{{scenes}}

Visual Plans:
{{visual_plans}}

For every scene decide the asset type: ai_video, ai_image, diagram, chart, icon, screenshot, animation_only, mixed_assets

Rules (AI video generation - no stock media):
1. ALWAYS use ai_video for all visual scenes. The pipeline generates real AI video clips (Google Veo) for every scene, so narrative, cinematic, and action content must use ai_video. Never pick ai_image for visual scenes - if video generation is unavailable the pipeline falls back to AI images automatically; that substitution happens downstream and is out of scope for this decision.
2. NEVER use stock_image, stock_footage, or stock_video - stock media returns irrelevant or mismatched results and is disabled in this pipeline.
3. Use diagram, chart, icon, or screenshot only when the scene is explicitly a data visualisation, infographic, or UI screenshot - NOT for narrative or cinematic scenes.
4. Provide a rough estimated_generation_cost for reference - the pipeline recalculates the real cost afterwards from actual provider pricing, so precision here is not critical.

Assign confidence score (0.0-1.0), estimate generation cost (USD), and rendering complexity (low, medium, high).

Respond with a JSON object containing:
{
  "decisions": [
    {
      "scene_id": "sc1",
      "asset_type": "ai_video",
      "confidence_score": 0.85,
      "estimated_generation_cost": 0.20,
      "estimated_rendering_complexity": "medium",
      "rationale": "Why this asset type was chosen"
    }
  ]
}

Provide only the JSON object, no additional text.""",
    version="2.3.0",
    description="Decides asset types - AI video (Veo) for visual scenes, diagram/chart/icon/screenshot for data visuals, no stock media; real cost is recalculated downstream from actual provider pricing"
)

CONTINUITY_PROMPT = PromptTemplate.from_string(
    "continuity",
    """You are a continuity expert. Ensure visual consistency across all scenes.

Topic: {{topic}}
Brand Style: {{brand_style}}

Scenes:
{{scenes}}

Visual Plans:
{{visual_plans}}

Camera Plans:
{{camera_plans}}

Check consistency of: characters, colors, objects, visual style, camera style, aspect ratio, lighting, transitions, and brand style.

Respond with a JSON object containing:
{
  "character_consistency": "Description of character consistency",
  "color_consistency": "Description of color consistency",
  "object_consistency": "Description of object consistency",
  "visual_style_consistency": "Description of visual style consistency",
  "camera_style_consistency": "Description of camera style consistency",
  "aspect_ratio": "16:9",
  "lighting_consistency": "Description of lighting consistency",
  "transition_consistency": "Description of transition consistency",
  "brand_style": "Description of brand style alignment",
  "issues": ["List of continuity issues found"],
  "consistency_score": 0.85
}

Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Validates visual consistency across all scenes"
)

STORYBOARD_REVIEW_PROMPT = PromptTemplate.from_string(
    "storyboard_review",
    """You are a storyboard review expert. Review the complete storyboard for quality.

Topic: {{topic}}
Total Scenes: {{scene_count}}
Total Duration: {{total_duration}} seconds
Estimated Budget: ${{estimated_budget}}

Scenes:
{{scenes}}

Visual Plans:
{{visual_plans}}

Camera Plans:
{{camera_plans}}

Animation Plans:
{{animation_plans}}

Asset Decisions:
{{asset_decisions}}

Continuity:
{{continuity}}

Validate: scene flow, visual variety, scene duration, continuity, camera variety, animation variety, cost estimate, rendering feasibility.

Respond with a JSON object containing:
{
  "scene_flow_score": 0.85,
  "visual_variety_score": 0.8,
  "scene_balance_score": 0.9,
  "narrative_consistency_score": 0.85,
  "camera_variety_score": 0.75,
  "animation_quality_score": 0.8,
  "budget_efficiency_score": 0.85,
  "rendering_feasibility_score": 0.9,
  "overall_score": 0.84,
  "issues": ["List of issues"],
  "strengths": ["List of strengths"],
  "recommendations": ["List of recommendations"],
  "passed": true
}

Scores should be 0.0 to 1.0. 'passed' is true if overall_score >= 0.7 and no critical issues.
Provide only the JSON object, no additional text.""",
    version="1.0.0",
    description="Reviews storyboard for scene flow, visual variety, continuity, and feasibility"
)
