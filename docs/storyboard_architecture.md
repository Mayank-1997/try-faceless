# Phase 8 — Storyboard & Scene Planning System Architecture

## Overview

The Storyboard & Scene Planning System transforms a finalized `ScriptPackage` into a production-ready storyboard. The system consists of 9 AI agents chained sequentially in a LangGraph workflow. The output is a structured `StoryboardPackage` with per-scene `ScenePackage` objects that downstream agents (Image, Video, Voice, Rendering) consume.

## Storyboard Workflow Diagram

```
Script Package
    │
    ▼
┌──────────────────┐
│ Story Analyzer   │  Analyzes narrative flow, emotional peaks, pacing,
│ Agent            │  scene boundaries, emphasis, dramatic moments,
│                  │  visual opportunities
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Story Beat Agent │  Converts script into story beats
│                  │  (introduction, conflict, explanation, reveal,
│                  │  transition, conclusion)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Scene            │  Splits script into production scenes
│ Segmentation     │  Each scene: number, timestamps, narration,
│ Agent            │  duration, goal, type
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Visual           │  For every scene generates visual description,
│ Storyboard Agent │  composition, foreground, background, objects,
│                  │  characters, environment, mood, lighting,
│                  │  color palette, depth, visual style
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Camera Planner   │  Determines camera angle, distance, lens,
│ Agent            │  movement, motion speed, focus point
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Animation        │  Plans element animation, text animation,
│ Planner Agent    │  camera motion, object motion, background motion,
│                  │  timing, transitions, scene effects
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Asset Decision   │  For every scene decides asset type
│ Agent            │  (AI image, AI video, stock, diagram, etc.)
│                  │  Assigns confidence, cost, complexity
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Continuity Agent │  Ensures consistency across scenes
│                  │  Tracks characters, colors, objects, style,
│                  │  camera, aspect ratio, lighting, brand
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Storyboard       │  Validates scene flow, visual variety, duration,
│ Review Agent     │  continuity, camera/animation variety, cost,
│                  │  rendering feasibility
│                  │  Assembles final StoryboardPackage
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Storyboard       │  Final output: story beats, scenes, visual plans,
│ Package          │  camera plans, animation plans, asset decisions,
│                  │  continuity, scene packages, budget, timeline
└──────────────────┘
```

## Scene Planning Diagram

```
Script Package
    │
    ▼
┌──────────────────────────────────────────┐
│         Scene Segmentation Agent         │
│                                          │
│  Input: Script + Story Beats             │
│  Output: List of PlannedScene            │
│                                          │
│  Each PlannedScene contains:             │
│  ├── scene_number (1, 2, 3...)           │
│  ├── scene_id (sc1, sc2, sc3...)         │
│  ├── title                               │
│  ├── start_timestamp                     │
│  ├── end_timestamp                       │
│  ├── narration                           │
│  ├── estimated_duration_seconds          │
│  ├── scene_goal                          │
│  └── scene_type                          │
│      ├── talking                         │
│      ├── diagram                         │
│      ├── animation                       │
│      ├── timeline                        │
│      ├── infographic                     │
│      ├── comparison                      │
│      ├── map                             │
│      ├── screenshot                      │
│      ├── code                            │
│      ├── product_demo                    │
│      ├── stock_footage                   │
│      ├── ai_image                        │
│      ├── ai_video                        │
│      └── mixed                           │
└──────────────────────────────────────────┘
```

## Camera Planning Diagram

```
Scenes + Visual Plans
    │
    ▼
┌──────────────────────────────────────────┐
│         Camera Planner Agent             │
│                                          │
│  For each scene determines:              │
│  ├── camera_angle                        │
│  │   ├── wide                            │
│  │   ├── medium                          │
│  │   ├── close_up                        │
│  │   ├── extreme_close_up                │
│  │   ├── overhead                        │
│  │   ├── low_angle                       │
│  │   ├── high_angle                      │
│  │   ├── dutch                           │
│  │   └── pov                             │
│  ├── camera_distance (far/medium/close)  │
│  ├── lens (wide/standard/telephoto/macro)│
│  ├── movement                            │
│  │   ├── static                          │
│  │   ├── pan_left / pan_right            │
│  │   ├── zoom_in / zoom_out              │
│  │   ├── tilt_up / tilt_down             │
│  │   ├── dolly_in / dolly_out            │
│  │   ├── tracking                        │
│  │   └── orbit                           │
│  ├── motion_speed (slow/normal/fast)     │
│  └── focus_point                         │
└──────────────────────────────────────────┘
```

## Animation Planning Diagram

```
Scenes + Visual Plans + Camera Plans
    │
    ▼
┌──────────────────────────────────────────┐
│       Animation Planner Agent            │
│                                          │
│  For each scene plans:                   │
│  ├── element_animation                   │
│  ├── text_animation                      │
│  ├── camera_motion                       │
│  ├── object_motion                       │
│  ├── background_motion                   │
│  ├── timing                              │
│  ├── entrance_transition                 │
│  ├── exit_transition                     │
│  └── scene_effects[]                     │
└──────────────────────────────────────────┘
```

## Storyboard Package Schema

```json
{
  "id": "UUID",
  "story_analysis": {
    "narrative_flow": "Introduction to conclusion",
    "emotional_peaks": ["Curiosity peak at 30s"],
    "pacing": "moderate",
    "scene_boundaries": ["Boundary at 30s"],
    "emphasis_points": ["AI definition"],
    "dramatic_moments": ["AI revelation"],
    "visual_opportunities": ["Show AI brain"]
  },
  "story_beats": {
    "beats": [
      {
        "beat_type": "introduction",
        "purpose": "Hook viewer",
        "emotion": "curious",
        "duration_seconds": 30,
        "importance": "high",
        "description": "Opening hook"
      }
    ],
    "total_beats": 3
  },
  "scenes": {
    "scenes": [
      {
        "scene_number": 1,
        "scene_id": "sc1",
        "title": "Intro",
        "start_timestamp": 0.0,
        "end_timestamp": 30.0,
        "narration": "Welcome to AI",
        "estimated_duration_seconds": 30,
        "scene_goal": "Introduce topic",
        "scene_type": "talking"
      }
    ],
    "total_scenes": 2,
    "total_duration_seconds": 180
  },
  "visual_plans": {
    "visual_plans": [
      {
        "scene_id": "sc1",
        "visual_description": "AI brain visualization",
        "composition": "Centered",
        "foreground": "AI brain",
        "background": "Dark gradient",
        "objects": ["neural network"],
        "characters": [],
        "environment": "Digital space",
        "mood": "curious",
        "lighting": "Soft blue",
        "color_palette": ["#FF0000", "#00FF00"],
        "depth": "deep",
        "visual_style": "modern"
      }
    ]
  },
  "camera_plans": {
    "camera_plans": [
      {
        "scene_id": "sc1",
        "camera_angle": "medium",
        "camera_distance": "medium",
        "lens": "standard",
        "movement": "static",
        "motion_speed": "normal",
        "focus_point": "Center"
      }
    ]
  },
  "animation_plans": {
    "animation_plans": [
      {
        "scene_id": "sc1",
        "element_animation": "Fade in",
        "text_animation": "Typewriter",
        "camera_motion": "Static",
        "object_motion": "Float",
        "background_motion": "Gradient",
        "timing": "2s delay",
        "entrance_transition": "Fade in",
        "exit_transition": "Fade out",
        "scene_effects": ["particle"]
      }
    ]
  },
  "asset_decisions": {
    "decisions": [
      {
        "scene_id": "sc1",
        "asset_type": "ai_image",
        "confidence_score": 0.85,
        "estimated_generation_cost": 0.05,
        "estimated_rendering_complexity": "low",
        "rationale": "Good for static visual"
      }
    ],
    "total_estimated_cost": 0.15
  },
  "continuity": {
    "character_consistency": "Consistent",
    "color_consistency": "Blue theme",
    "visual_style_consistency": "Modern",
    "camera_style_consistency": "Coherent",
    "aspect_ratio": "16:9",
    "consistency_score": 0.85,
    "issues": []
  },
  "review": {
    "scene_flow_score": 0.85,
    "visual_variety_score": 0.8,
    "overall_score": 0.84,
    "passed": true
  },
  "quality": {
    "visual_diversity": 0.8,
    "scene_balance": 0.9,
    "narrative_consistency": 0.85,
    "camera_variety": 0.75,
    "animation_quality": 0.8,
    "budget_efficiency": 0.85,
    "overall_production_score": 0.84
  },
  "scene_packages": [
    {
      "scene_id": "sc1",
      "scene_number": 1,
      "title": "Intro",
      "narration": "Welcome to AI",
      "duration_seconds": 30,
      "visual_prompt_summary": "AI brain visualization",
      "asset_type": "ai_image",
      "camera_plan": {...},
      "animation_plan": {...},
      "visual_plan": {...},
      "transition": "Fade in",
      "priority": "medium",
      "dependencies": [],
      "estimated_cost": 0.05,
      "estimated_tokens": 0,
      "quality_score": 0.84
    }
  ],
  "estimated_budget": 0.15,
  "estimated_timeline_minutes": 3,
  "version": 1
}
```

## Scene Package Structure

Each `ScenePackage` includes:
- **Scene ID**: Unique identifier (sc1, sc2, etc.)
- **Scene Number**: Sequential number
- **Title**: Scene title
- **Narration**: Spoken text for this scene
- **Duration**: Estimated duration in seconds
- **Visual Prompt Summary**: Summary of visual description
- **Asset Type**: Chosen asset type (ai_image, ai_video, etc.)
- **Camera Plan**: Camera angle, distance, lens, movement, speed, focus
- **Animation Plan**: Element, text, camera, object, background animations
- **Visual Plan**: Full visual description with composition, mood, lighting, colors
- **Transition**: Transition to next scene
- **Priority**: Production priority (low, medium, high, critical)
- **Dependencies**: List of dependent scene IDs
- **Estimated Cost**: Generation cost estimate
- **Estimated Tokens**: Token usage estimate
- **Quality Score**: Overall quality score

## Key Components

### Storyboard Schema (`src/ai/agents/storyboard/schema.py`)

All Pydantic v2 models:
- `StoryAnalysis` — Narrative analysis
- `StoryBeat`, `StoryBeatResult` — Story beats
- `PlannedScene`, `SceneSegmentationResult` — Scene segmentation
- `VisualPlan`, `VisualStoryboardResult` — Visual descriptions
- `CameraPlan`, `CameraPlanResult` — Camera plans
- `AnimationPlan`, `AnimationPlanResult` — Animation plans
- `AssetSceneDecision`, `AssetDecisionResult` — Asset decisions
- `ContinuityResult` — Continuity validation
- `StoryboardReviewResult` — Review results
- `StoryboardQualityEvaluation` — Quality evaluation
- `ScenePackage` — Per-scene aggregated package
- `StoryboardPackage` — Final output combining all results

### Storyboard Prompts (`src/ai/agents/storyboard/prompts.py`)

9 versioned prompt templates:
- `STORY_ANALYZER_PROMPT` — Narrative analysis
- `STORY_BEAT_PROMPT` — Story beat generation
- `SCENE_SEGMENTATION_PROMPT` — Scene segmentation
- `VISUAL_STORYBOARD_PROMPT` — Visual descriptions
- `CAMERA_PLANNER_PROMPT` — Camera planning
- `ANIMATION_PLANNER_PROMPT` — Animation planning
- `ASSET_DECISION_PROMPT` — Asset decisions
- `CONTINUITY_PROMPT` — Continuity validation
- `STORYBOARD_REVIEW_PROMPT` — Storyboard review

### Storyboard Events (`src/ai/agents/storyboard/events.py`)

11 storyboard-specific events:
- `StoryboardStarted` — Workflow begins
- `StoryAnalyzed` — Analysis completed
- `BeatsGenerated` — Beats created
- `ScenesPlanned` — Scenes segmented
- `VisualStoryboardGenerated` — Visual plans created
- `CameraPlanned` — Camera plans created
- `AnimationPlanned` — Animation plans created
- `AssetDecisionCompleted` — Asset decisions made
- `ContinuityValidated` — Continuity checked
- `StoryboardReviewed` — Review completed
- `StoryboardCompleted` — Package assembled

### Storyboard Workflow Graph (`src/ai/agents/storyboard/workflow.py`)

`StoryboardWorkflowGraph` extends `BaseWorkflowGraph`:
- 9 nodes (one per agent)
- 8 sequential edges
- Entry: `story_analyzer`
- Exit: `storyboard_review`

## State Management

All agent outputs are persisted into `WorkflowState.storyboard.metadata`:
- `metadata["story_analysis"]` — StoryAnalysis dict
- `metadata["story_beats"]` — StoryBeatResult dict
- `metadata["scenes"]` — SceneSegmentationResult dict
- `metadata["visual_plans"]` — VisualStoryboardResult dict
- `metadata["camera_plans"]` — CameraPlanResult dict
- `metadata["animation_plans"]` — AnimationPlanResult dict
- `metadata["asset_decisions"]` — AssetDecisionResult dict
- `metadata["continuity"]` — ContinuityResult dict
- `metadata["review"]` — StoryboardReviewResult dict
- `metadata["storyboard_package"]` — Final StoryboardPackage dict

The `StoryboardData` model in `WorkflowState` was extended with a `metadata` field to store these structured outputs.

## Quality Evaluation

The storyboard is evaluated on multiple dimensions:
- **Visual Diversity**: Variety of visual styles across scenes
- **Scene Balance**: Balance of scene types and durations
- **Narrative Consistency**: Consistency with script narrative
- **Camera Variety**: Variety of camera angles and movements
- **Animation Quality**: Quality and appropriateness of animations
- **Budget Efficiency**: Cost-effectiveness of asset decisions
- **Overall Production Score**: Weighted combination of all dimensions

## Testing

74 unit tests in `tests/unit/test_storyboard_agents.py`:
- Schema tests (all Pydantic models)
- Agent tests (each of the 9 agents)
- Workflow graph tests (node registration, edges, chain)
- Event tests (all 11 storyboard events)
- Prompt template tests (all 9 templates)
- Full pipeline integration test (all 9 agents in sequence)
