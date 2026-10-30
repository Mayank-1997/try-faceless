# Prompt Templates

Every AI prompt is stored as a separate versioned file in this directory.

## Structure

```
prompts/
├── topic/          # Topic expansion and refinement
├── research/       # Web research and fact-gathering
├── story/          # Story planning and narrative structure
├── script/         # Script writing (narration, dialogue)
├── scene/          # Scene planning and storyboard
├── asset/          # Asset decision (cost-optimised visual strategy)
├── image/          # Image generation prompts
├── video/          # Video generation prompts
├── voice/          # Voice/TTS instructions
├── thumbnail/      # Thumbnail generation
├── seo/            # SEO optimization (title, description, tags)
└── publish/        # Publishing metadata
```

## Versioning

Each prompt file follows the naming convention:

```
<prompt_name>.v<major>.<minor>.md
```

Example: `research_web_search.v1.0.md`

The prompt manager loads the latest version by default but can pin
to a specific version for reproducibility.
