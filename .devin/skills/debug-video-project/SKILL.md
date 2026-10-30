---
name: debug-video-project
description: Debug a video-generation run end-to-end — trace prompt drift, asset generation, and rendering for a project ID
argument-hint: "<project_id> [workflow_id]"
allowed-tools:
  - read
  - grep
  - glob
  - exec
---

# Debug a video project

The user gave you a project ID (and optionally a workflow ID). Investigate the run end-to-end and report what happened — especially where the user's intent diverged from the output. Do NOT modify files; this is a read-only investigation.

If no workflow_id is given, use the most recent one (latest directory/file by timestamp under `storage/workflow_state/<project_id>/`).

## Step 1 — Read the workflow state

Read `storage/workflow_state/<project_id>/<workflow_id>/workflow_state.json`. Trace intent drift through these keys in order:

1. `topic.raw_topic` — what the user actually asked for (title + description from the UI)
2. `topic.expanded_topic` + `research.summary` — how the research agents reinterpreted it. Flag if the expanded topic pivots to a different subject (e.g. a literal cinematic prompt about a cliff jump gets treated as a topic *about AI video tech* because it mentions Sora/Runway/etc.)
3. `script.content` / `script.hook` — the narration written by script agents
4. `storyboard.metadata.storyboard_package.scene_packages[]` — per-scene `visual_plan.visual_description`, `camera_plan`, `asset_type`, `duration_seconds`
5. `assets[]` — `asset_type`, `provider` (expect `veo` for video when USE_VEO=true), `cost_usd`, `file_path`
6. `scenes[].visual_type` — expect `ai_video` for generated clips

Report exactly which step first diverged from the user's stated intent.

## Step 2 — Check generated files on disk

`ls -la` these paths under `storage/projects/<project_id>/`:
- `videos/` — per-scene Veo clips (scene_N.mp4)
- `images/` — still images (only present if Veo failed/disabled — flag this)
- `voice/`, `subtitles/` — TTS + SRT per scene
- `.render_parts_<workflow_id>/` — intermediate render clips
- `final_video.mp4` — exists only if RENDERING completed

Missing dirs indicate which pipeline stage never ran or fell back.

## Step 3 — Check container logs for errors

```bash
docker compose logs --tail=200 celery_worker | grep -iE "error|traceback|failed|veo_scene"
docker compose logs --tail=100 api | grep -iE "error|traceback"
```

Look for `veo_scene_generation_failed` (Veo call failed → silent image fallback), DB errors, or import crashes.

## Step 4 — Check environment/config assumptions

- `grep -iE "USE_VEO|VEO_|COST_VEO" .env` — confirm video generation is actually enabled
- `docker ps --format "{{.Names}} {{.Status}}" | grep aivideo` — all 6 containers should be Up

## Step 5 — Report

Summarize as:
1. **What the user asked** (from `raw_topic`, in one line)
2. **What the pipeline actually produced** (scene descriptions + asset types)
3. **First divergence point** (which agent/step rewrote the intent)
4. **Concrete evidence** (file paths, JSON keys, log lines)
5. **Likely fix** — prompt-level (rephrase the description) or code-level (which file/function)
