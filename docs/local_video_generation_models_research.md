# Local Free Video Generation Models Research

Research date: 2026-09-09

## Executive Summary

There is currently **no free local model that is truly equivalent to Google Veo 3 / Veo 3.1** across all dimensions: prompt following, realistic physics, temporal consistency, 1080p/4K quality, native audio, camera control, and production reliability. Veo runs on large managed infrastructure and its strongest versions are not designed for consumer local execution.

For heavy local usage, the most practical strategy is:

1. **Primary local model:** **Wan2.1 / Wan2.x**, especially **Wan2.1 T2V/I2V 14B** if you have high VRAM, or **Wan2.1 T2V 1.3B** for cheaper high-volume 480p generation.
2. **Best low-VRAM long-video option:** **FramePack**, because it is designed for long generation with aggressive memory management and can run on much smaller GPUs.
3. **Fast iteration / pipeline-friendly option:** **LTX-Video**, especially distilled models, for speed and iteration.
4. **High-quality but expensive local option:** **HunyuanVideo** or **Mochi 1**, but these are realistically workstation/datacenter models unless using optimized ComfyUI workflows.
5. **Budget fallback:** **CogVideoX**, especially CogVideoX-2B/5B, for lower hardware requirements but generally below Veo/Wan/Hunyuan/Mochi quality.

For this project, which already has an AI/stock asset generation pipeline, the most sensible local integration target is **Wan2.1 via ComfyUI or a dedicated Python worker**, with **FramePack** as a second backend for long clips or low-VRAM machines.

## Important Reality Check: “Equivalent to Veo”

Google Veo 3/3.1 offers capabilities that local open models generally do not match yet:

- Native synchronized audio/dialogue generation.
- Strong realistic physics and motion coherence.
- High prompt adherence across cinematic instructions.
- Better temporal consistency for characters and scene continuity.
- 1080p/4K production-grade outputs with cloud-scale compute.
- Managed safety, scaling, queueing, retries, and model serving.

Local open models can produce impressive clips, but for YouTube automation with heavy video generation, expect to use a pipeline:

```text
storyboard prompt
  -> image generation / keyframe generation
  -> image-to-video generation
  -> interpolation / upscaling
  -> audio/TTS/subtitles
  -> FFmpeg composition
```

This is more reliable than asking a local text-to-video model to generate the whole final video directly.

## Recommended Models

| Rank | Model | Best Use | Local Practicality | Quality vs Veo | License / Access |
|------|-------|----------|-------------------|----------------|------------------|
| 1 | Wan2.1 / Wan2.x | Best all-around local T2V/I2V | Good with 1.3B; demanding with 14B | Closest practical open option | Open weights; check model license before commercial use |
| 2 | FramePack | Long videos, low VRAM, desktop use | Excellent | Good, especially for long generated motion | Open repo; check model license |
| 3 | LTX-Video | Fast iteration, ComfyUI workflows | Good to medium depending model size | Good, not always Veo-level realism | Apache 2.0 code; check weights/license |
| 4 | HunyuanVideo | High-quality cinematic generation | Poor unless 45-80GB VRAM | Strong open-model quality | Open weights; check license |
| 5 | Mochi 1 | High-fidelity motion | Poor unless H100-class or optimized workflow | Strong motion, good prompt following | Apache 2.0 |
| 6 | CogVideoX | Lower-cost local generation | Good with optimizations | Useful but generally lower quality | Some Apache 2.0 variants; check each checkpoint |

## 1. Wan2.1 / Wan2.x

### Why consider it

Wan2.1 is one of the best open video generation suites for local use. It has multiple checkpoints for text-to-video, image-to-video, and other video tasks. The project specifically advertises consumer GPU support for the smaller 1.3B model.

### Strengths

- Strong open-model visual quality.
- Text-to-video and image-to-video variants.
- 1.3B model can run on consumer GPUs.
- 14B variants support better quality and higher resolutions.
- Good candidate for ComfyUI integration.

### Weaknesses

- 14B models require serious VRAM for efficient heavy usage.
- No native Veo-style audio generation.
- Long videos still need scene chaining and post-processing.
- Quality depends heavily on prompt engineering, seed selection, and upscaling.

### Reported requirements

From the Wan2.1 project documentation:

- **Wan2.1 T2V-1.3B**:
  - About **8.19GB VRAM** for 5-second 480p generation.
  - Example performance: about **4 minutes for a 5-second 480p clip on RTX 4090** without extra optimizations.
- **Wan2.1 14B variants**:
  - Higher quality, supports 480p/720p depending checkpoint.
  - Practical heavy use generally needs **24GB+ VRAM**, and more is better.

### Practical local config

Minimum useful:

```text
GPU: NVIDIA RTX 3060 12GB / RTX 4060 Ti 16GB
VRAM: 12-16GB
RAM: 32GB
Storage: 500GB free NVMe
OS: Windows or Linux, Linux preferred for fewer CUDA issues
Use case: 480p experiments, short clips, low concurrency
```

Recommended heavy usage:

```text
GPU: RTX 4090 24GB or RTX 5090-class 24GB/32GB
VRAM: 24GB+
RAM: 64GB+
Storage: 1-2TB NVMe
OS: Ubuntu 22.04/24.04 or WSL2 with NVIDIA CUDA passthrough
Use case: repeated 480p/720p clips, queue-based generation
```

Best workstation:

```text
GPU: RTX 6000 Ada 48GB, A6000 48GB, L40S 48GB, A100 80GB, H100 80GB
VRAM: 48-80GB
RAM: 128GB+
Storage: 2TB+ NVMe
OS: Linux
Use case: heavy 14B usage, parallel queues, fewer offload slowdowns
```

### Recommendation for this repo

Use **Wan2.1 I2V 14B** when you can afford the GPU. For YouTube automation, image-to-video is usually more controllable than text-to-video because the storyboard can first create deterministic keyframes, then animate them.

If hardware is limited, use **Wan2.1 T2V 1.3B** for cheap local tests and previews, then selectively use a stronger model for final clips.

## 2. FramePack

### Why consider it

FramePack is designed as practical desktop software for local video generation with very aggressive memory management. It is especially interesting if you want long videos or cannot afford 24GB+ VRAM.

### Strengths

- Very low stated VRAM requirement.
- Windows and Linux support.
- Designed for long videos.
- Good desktop usability.
- Good option for heavy generation where cost is more important than maximum quality.

### Weaknesses

- Speed can be slow on lower-end GPUs.
- Quality may not equal the strongest Wan/Hunyuan/Mochi outputs.
- Integration into a backend service may require wrapping its workflow or scripts.

### Reported requirements

From the FramePack project documentation:

- NVIDIA RTX 30xx/40xx/50xx GPU with fp16/bf16 support.
- Windows or Linux.
- At least **6GB GPU memory**.
- Claims 1-minute video generation with a 13B model can fit in 6GB VRAM.
- Example speed on RTX 4090: around **2.5 seconds/frame unoptimized**, around **1.5 seconds/frame with teacache**.

### Practical local config

Minimum useful:

```text
GPU: RTX 3060 6GB/12GB, RTX 4060 8GB, laptop RTX 3060+
VRAM: 6-8GB
RAM: 32GB
Storage: 500GB NVMe
OS: Windows or Linux
Use case: long local video generation with low upfront hardware cost
```

Recommended heavy usage:

```text
GPU: RTX 4090 24GB or better
VRAM: 24GB+
RAM: 64GB+
Storage: 1TB+ NVMe
OS: Linux preferred, Windows acceptable
Use case: high-volume long clip generation
```

### Recommendation for this repo

Use FramePack as a **secondary local backend** for long or low-cost scenes where exact cinematic realism is less important than generating lots of usable motion cheaply.

## 3. LTX-Video

### Why consider it

LTX-Video is designed for high-speed video generation and has official ComfyUI workflows. It is useful for rapid iteration and pipeline integration.

### Strengths

- Strong focus on speed.
- ComfyUI workflows are available and recommended by the project.
- Multiple model sizes, including distilled variants.
- Good fit for local experimentation and queued batch generation.

### Weaknesses

- Highest-quality 13B models need more VRAM.
- Distilled/smaller models trade quality for speed.
- May not match Veo-level realism or prompt-following.

### Reported requirements

From LTX-Video package/repo documentation:

- Python >= 3.10.
- Tested with Python 3.10.5 and CUDA 12.2.
- Supports PyTorch >= 2.1.2.
- macOS MPS support has been tested in some configurations, but NVIDIA CUDA is preferred.
- Model family includes 13B and 2B/distilled variants.

### Practical local config

Minimum useful:

```text
GPU: RTX 3060 12GB / RTX 4060 Ti 16GB
VRAM: 12-16GB
RAM: 32GB
Storage: 500GB NVMe
Use case: lower-res or distilled model generation
```

Recommended heavy usage:

```text
GPU: RTX 4090 24GB or RTX 5090-class
VRAM: 24GB+
RAM: 64GB+
Storage: 1TB+ NVMe
Use case: fast iteration, ComfyUI workflows, batch generation
```

### Recommendation for this repo

Use LTX-Video for **preview generation** and **fast iteration**. It can help decide whether a prompt/scene works before spending time on Wan/Hunyuan/Mochi.

## 4. HunyuanVideo

### Why consider it

HunyuanVideo is a high-quality open video model from Tencent. It is closer to the premium model category, but the official requirements are high.

### Strengths

- Strong quality among open models.
- Text-to-video and image-to-video ecosystem support.
- Multi-GPU sequence parallel inference support.
- FP8 quantized weights are available according to the project.

### Weaknesses

- Official local requirements are not consumer-friendly.
- Linux-focused.
- Heavy usage on consumer GPUs will require quantization/offloading and will be slow.

### Reported requirements

From the HunyuanVideo project documentation:

- NVIDIA CUDA GPU required.
- Tested on a single 80GB GPU.
- Minimum GPU memory:
  - **60GB VRAM** for 720x1280x129 frames.
  - **45GB VRAM** for 544x960x129 frames.
- Recommended: **80GB VRAM**.
- Tested OS: Linux.
- Recommended CUDA: 12.4 or 11.8.
- Python environment: project documentation uses Python 3.10.9.

### Practical local config

Minimum practical:

```text
GPU: RTX 6000 Ada 48GB / A6000 48GB / L40S 48GB
VRAM: 48GB
RAM: 128GB
Storage: 2TB NVMe
OS: Linux
Use case: reduced-resolution generation, offloading/quantization likely needed
```

Recommended:

```text
GPU: A100 80GB or H100 80GB
VRAM: 80GB
RAM: 128-256GB
Storage: 2TB+ NVMe
OS: Linux
Use case: serious high-quality local generation
```

### Recommendation for this repo

Do not choose HunyuanVideo as the first local backend unless you have workstation/datacenter GPUs. It is a quality candidate, but not the best cost/performance option for heavy generation on a normal desktop.

## 5. Mochi 1

### Why consider it

Mochi 1 is a strong open video model with good motion quality and a permissive Apache 2.0 license.

### Strengths

- Strong motion quality.
- Good open-model prompt adherence.
- Apache 2.0 license.
- Multi-GPU operation supported.

### Weaknesses

- Official single-GPU inference requires about 60GB VRAM.
- Recommended hardware is at least one H100.
- Consumer-GPU operation typically needs ComfyUI optimizations and quality/speed tradeoffs.

### Reported requirements

From Mochi documentation:

- About **60GB VRAM** for single-GPU operation in the official repo.
- Multi-GPU model splitting supported.
- ComfyUI can reportedly run optimized Mochi workflows under 20GB VRAM, but that is not the official baseline.
- FFmpeg is needed to turn outputs into videos.

### Practical local config

Minimum practical with official repo:

```text
GPU: RTX 6000 Ada 48GB may still be tight; A100/H100 preferred
VRAM: 60GB+
RAM: 128GB
Storage: 1-2TB NVMe
OS: Linux
```

Consumer optimized route:

```text
GPU: RTX 4090 24GB
VRAM: 24GB
RAM: 64GB
Storage: 1TB NVMe
OS: Linux or Windows with ComfyUI
Use case: optimized ComfyUI workflows, not official full-quality path
```

### Recommendation for this repo

Use Mochi only if you specifically want high-quality motion experiments or if ComfyUI workflows prove stable on your machine. It is not the easiest backend for automated heavy generation.

## 6. CogVideoX

### Why consider it

CogVideoX is accessible and has lower VRAM paths through Diffusers optimizations and quantization. It is useful for budget local generation and experimentation.

### Strengths

- 2B model can run on older/lower-end GPUs with optimizations.
- 5B model is feasible on consumer desktops with quantization/offloading.
- Diffusers integration exists.
- Useful for experimentation and fallback generation.

### Weaknesses

- Quality is usually below Wan/Hunyuan/Mochi and far below Veo for difficult prompts.
- Resolution/frame constraints vary by checkpoint.
- English prompts are generally recommended.

### Reported requirements

From CogVideo/CogVideoX documentation:

- CogVideoX-2B:
  - 720x480, 6 seconds, 8 FPS.
  - Diffusers FP16 can start from around **4GB VRAM** with optimizations.
  - INT8 can start from around **3.6GB VRAM**.
- CogVideoX-5B:
  - Diffusers BF16 can start from around **5GB VRAM** with optimizations.
  - INT8 can start from around **4.4GB VRAM**.
  - Without optimizations, VRAM usage is much higher.
- CogVideoX1.5-5B:
  - Higher resolution, but significantly more demanding unless optimized.

### Practical local config

Minimum useful:

```text
GPU: RTX 3060 12GB or similar
VRAM: 8-12GB
RAM: 32GB
Storage: 500GB NVMe
Use case: budget/preview generation
```

Recommended:

```text
GPU: RTX 4090 24GB
VRAM: 24GB
RAM: 64GB
Storage: 1TB NVMe
Use case: faster generation, fewer offload slowdowns
```

### Recommendation for this repo

Use CogVideoX as a **fallback backend** or for preview clips, not as the main Veo replacement.

## Hardware Recommendations for Heavy Local Video Generation

### Tier 1: Entry-Level Local Testing

```text
GPU: RTX 3060 12GB / RTX 4060 Ti 16GB
VRAM: 12-16GB
CPU: 8+ cores
RAM: 32GB
Storage: 500GB-1TB NVMe
OS: Windows 11 or Ubuntu Linux
Best models: Wan2.1 1.3B, FramePack, CogVideoX, smaller/distilled LTX
Expected workflow: low-res clips, previews, slow batch generation
```

This tier is good for learning and testing, but not ideal for heavy production.

### Tier 2: Best Consumer Workstation

```text
GPU: RTX 4090 24GB or RTX 5090-class 24GB/32GB
VRAM: 24-32GB
CPU: 12-24 cores
RAM: 64-128GB
Storage: 2TB NVMe recommended
OS: Ubuntu Linux preferred; Windows acceptable for ComfyUI/FramePack
Best models: Wan2.1 14B with optimizations, FramePack, LTX-Video, CogVideoX 5B, optimized Mochi/Hunyuan workflows
Expected workflow: high-volume 480p/720p generation, queue-based automation, upscaling after generation
```

This is the best practical local setup for heavy usage without buying datacenter GPUs.

### Tier 3: Serious Local Production

```text
GPU: RTX 6000 Ada 48GB / A6000 48GB / L40S 48GB
VRAM: 48GB
CPU: 24+ cores
RAM: 128GB+
Storage: 2-4TB NVMe
OS: Linux
Best models: Wan2.1 14B, HunyuanVideo reduced settings, Mochi optimized, LTX 13B
Expected workflow: stronger quality, fewer offload penalties, better batch throughput
```

This tier is expensive but much more realistic for local production.

### Tier 4: Datacenter-Class Local/Private Server

```text
GPU: A100 80GB / H100 80GB / multi-GPU L40S/A6000
VRAM: 80GB+ or multiple 48GB GPUs
CPU: 32+ cores
RAM: 256GB+
Storage: 4TB+ NVMe
OS: Linux
Best models: HunyuanVideo, Mochi official, Wan 14B, multi-GPU inference
Expected workflow: closest open-model experience to cloud video generation
```

This is the only tier where HunyuanVideo/Mochi official requirements become comfortable.

## Software Configuration

### Recommended OS

For heavy usage, prefer:

```text
Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
NVIDIA Driver: recent stable production driver
CUDA: match the model stack; CUDA 12.1/12.4/12.6 are common
Python: usually 3.10 or 3.11 for video model repos
PyTorch: install CUDA-specific wheel, not CPU-only wheel
```

Windows can work, especially for ComfyUI and FramePack, but Linux is usually easier for CUDA extensions such as FlashAttention, xFormers, SageAttention, and optimized kernels.

### Recommended Python/Environment Layout

Do **not** install all video models into this project’s backend venv. Keep each model isolated:

```text
C:\ai-models\wan21\venv
C:\ai-models\framepack\venv
C:\ai-models\ltx-video\venv
```

or on Linux:

```text
/opt/ai-models/wan21/.venv
/opt/ai-models/framepack/.venv
/opt/ai-models/ltx-video/.venv
```

Reasons:

- Video repos often pin incompatible PyTorch/Diffusers/Transformers versions.
- CUDA extension builds can break unrelated backend dependencies.
- Easier to upgrade one model without breaking the app.

### Queue/Service Architecture for This Project

For heavy usage, do not run generation inside the FastAPI request process. Use a local worker service:

```text
FastAPI backend
  -> Celery task / generation executor
  -> Local video generation service API
  -> Model-specific worker queue
  -> Output MP4 saved to storage/
```

Recommended local service approaches:

1. **ComfyUI API backend**
   - Best if using community workflows for Wan, LTX, Mochi, Hunyuan, FramePack.
   - Easier to swap models.
   - Good for rapid experimentation.

2. **Dedicated Python microservice per model**
   - Better for production control.
   - Cleaner logging, retries, job IDs, and storage paths.
   - More engineering work.

3. **CLI wrapper worker**
   - Fastest to implement.
   - Celery task shells out to model repo script.
   - Less robust, but acceptable for local-only usage.

## Throughput Expectations

Local video generation is slow compared to image generation. Heavy use requires queueing and caching.

Approximate expectations:

| Hardware | Expected Throughput |
|----------|---------------------|
| 12GB GPU | Good for experiments and overnight batches, not fast production |
| 24GB RTX 4090 | Practical for heavy solo usage, but still minutes per short clip for many models |
| 48GB workstation GPU | Much better stability and less offloading; good for production batches |
| 80GB datacenter GPU | Best local/private quality and speed, closest to cloud experience |

For YouTube automation, generate **short scene clips** and compose them with FFmpeg instead of generating a full video in one model call.

## Recommended Project Strategy

### Best practical setup

```text
Primary: Wan2.1 image-to-video
Secondary: FramePack for long/low-VRAM clips
Preview: LTX-Video distilled or CogVideoX
Post: FFmpeg composition + upscaling + interpolation if needed
Audio: keep existing TTS/subtitle pipeline
```

### Generation flow

```text
1. Storyboard creates visual prompt per scene.
2. Generate or select a keyframe image.
3. Run image-to-video model for 3-6 seconds per scene.
4. Save scene video asset to storage.
5. Compose with voice, subtitles, transitions, and music using FFmpeg.
6. Optional: upscale/interpolate final output.
```

This is more reliable than pure text-to-video for every scene.

## Recommended Local Config for You

If you plan **heavy usage** and want the best cost/performance:

```text
GPU: NVIDIA RTX 4090 24GB minimum; prefer RTX 5090-class 32GB if available
CPU: Ryzen 9 / Core i9 / Threadripper class, 12+ cores
RAM: 64GB minimum; 128GB preferred
Storage: 2TB NVMe dedicated to models/cache/output
OS: Ubuntu Linux preferred; Windows 11 acceptable if using ComfyUI/FramePack
Power/Cooling: strong PSU and cooling; generation keeps GPU loaded for long periods
```

If budget allows and this is production-critical:

```text
GPU: RTX 6000 Ada 48GB / L40S 48GB / A6000 48GB
RAM: 128GB+
Storage: 4TB NVMe
OS: Linux
```

If you want to approximate Veo quality locally, **VRAM matters more than almost anything else**. A 48GB GPU is a major quality-of-life upgrade over 24GB because it reduces CPU offload and enables larger models/settings.

## Practical Recommendation

For this codebase, start with:

1. **ComfyUI + Wan2.1 workflows** for local video generation.
2. Add a local `video_gateway` provider that sends jobs to ComfyUI or a local worker.
3. Generate per-scene 3-6 second clips, not full videos.
4. Cache outputs by prompt/model/seed to avoid regenerating expensive clips.
5. Keep TTS, subtitles, and FFmpeg rendering in the existing pipeline.

Do not start with HunyuanVideo or Mochi as the main backend unless you already have 48-80GB VRAM. They are strong models, but not the most efficient first choice for heavy local generation.

## Sources Checked

- Wan2.1 GitHub / Hugging Face documentation.
- Tencent HunyuanVideo GitHub documentation.
- Lightricks LTX-Video GitHub / PyPI documentation.
- Genmo Mochi GitHub / Hugging Face documentation.
- CogVideoX GitHub / Hugging Face / Diffusers documentation.
- FramePack GitHub documentation.
- Google DeepMind Veo public model page for baseline capability comparison.
