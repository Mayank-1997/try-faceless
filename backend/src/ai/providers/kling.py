"""Kling video generation provider — concrete implementation of ``VideoProvider``.

Wraps Kling v3 hosted on the fal.ai queue API behind the common
``VideoProvider`` interface.  No fal SDK is required — the queue API is
plain REST::

    POST   https://queue.fal.run/{endpoint}           -> {"request_id": ...}
    GET    https://queue.fal.run/{endpoint}/requests/{id}/status
    GET    https://queue.fal.run/{endpoint}/requests/{id}   -> {"video": {"url": ...}}

Endpoints used (``KLING_ENDPOINT`` base, default ``fal-ai/kling-video/v3/standard``):

- ``{endpoint}/text-to-video``  — initial clip generation.
- ``{endpoint}/image-to-video`` — extension chaining.  Kling has no native
  video-extension endpoint on fal, so ``extend_video`` extracts the last
  frame of the accumulated video with FFmpeg, feeds it as ``start_image_url``
  (base64 data URI), then concatenates the new clip onto the previous bytes
  so callers keep receiving the full combined video — the same contract Veo's
  server-side extension exposed.

Model constraints (Kling v3 on fal):
- ``duration`` is a string enum covering 3–15 seconds per call.
- Aspect ratio is ``16:9``, ``9:16`` or ``1:1``.
- ``generate_audio`` produces native audio (wind, ambience, EN/ZH speech).
- Output is delivered as an MP4 download URL on the queue result.

Auth: ``Authorization: Key {FAL_KEY}``.
"""

from __future__ import annotations

import asyncio
import base64
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from src.core.enums import AIProvider
from src.core.exceptions import (
    AIProviderError,
    AIProviderTimeoutError,
    ProviderNotInitializedError,
)
from src.core.interfaces import (
    HealthStatus,
    ProviderConfig,
    VideoGenerationPayload,
    VideoProvider,
)
from src.core.logging import get_logger

_KLING_MIN_SECONDS = 3
_KLING_MAX_SECONDS = 15

# fal.ai queue API base.  Endpoint paths such as
# "fal-ai/kling-video/v3/standard/text-to-video" are appended to it.
_FAL_QUEUE_BASE = "https://queue.fal.run"

# How often to poll the fal queue while a request is in progress.
_POLL_INTERVAL_SECONDS = 5


def quantize_kling_duration(seconds: float) -> int:
    """Clamp a requested duration to Kling's supported 3–15 second range."""
    return max(_KLING_MIN_SECONDS, min(_KLING_MAX_SECONDS, round(float(seconds))))


def _concat_mp4(first: bytes, second: bytes) -> bytes:
    """Concatenate two MP4 clips with FFmpeg and return the combined bytes.

    Both clips come from the same model at identical settings, so a
    stream-copy concat is attempted first; if the container streams are
    incompatible it falls back to a re-encode.
    """
    with tempfile.TemporaryDirectory(prefix="kling_concat_") as tmp:
        tmp_dir = Path(tmp)
        a_path = tmp_dir / "a.mp4"
        b_path = tmp_dir / "b.mp4"
        out_path = tmp_dir / "out.mp4"
        list_path = tmp_dir / "list.txt"
        a_path.write_bytes(first)
        b_path.write_bytes(second)
        list_path.write_text(f"file 'a.mp4'\nfile 'b.mp4'\n")

        copy_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_path), "-c", "copy", str(out_path),
        ]
        proc = subprocess.run(copy_cmd, capture_output=True)
        if proc.returncode != 0 or not out_path.exists():
            encode_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(list_path),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "128k",
                str(out_path),
            ]
            proc = subprocess.run(encode_cmd, capture_output=True)
            if proc.returncode != 0 or not out_path.exists():
                raise AIProviderError(
                    AIProvider.KLING.value,
                    f"FFmpeg concat failed: {proc.stderr.decode(errors='replace')[-500:]}",
                )
        return out_path.read_bytes()


def _last_frame_png(video_bytes: bytes) -> bytes:
    """Extract the last frame of an MP4 as PNG bytes via FFmpeg."""
    with tempfile.TemporaryDirectory(prefix="kling_frame_") as tmp:
        tmp_dir = Path(tmp)
        in_path = tmp_dir / "in.mp4"
        out_path = tmp_dir / "last.png"
        in_path.write_bytes(video_bytes)
        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-sseof", "-0.1", "-i", str(in_path),
                "-update", "1", "-frames:v", "1", str(out_path),
            ],
            capture_output=True,
        )
        if proc.returncode != 0 or not out_path.exists():
            raise AIProviderError(
                AIProvider.KLING.value,
                f"FFmpeg last-frame extraction failed: {proc.stderr.decode(errors='replace')[-500:]}",
            )
        return out_path.read_bytes()


class KlingProvider(VideoProvider):
    """Kling v3 (fal.ai) implementation of the ``VideoProvider`` interface."""

    def __init__(self) -> None:
        self._config: ProviderConfig | None = None
        self._logger = get_logger(__name__)
        self._initialized = False
        self._cost_per_second: float = 0.126
        self._api_key: str = ""
        self._endpoint: str = "fal-ai/kling-video/v3/standard"
        self._model_name: str = "kling-v3-standard"
        self._generate_audio: bool = True

    @property
    def provider_name(self) -> AIProvider:
        return AIProvider.KLING

    @property
    def model_name(self) -> str:
        return self._model_name

    async def initialize(self, config: ProviderConfig) -> None:
        self._config = config
        self._cost_per_second = config.extra.get("cost_per_second", 0.126)
        self._api_key = config.api_key or config.extra.get("fal_key", "")
        self._generate_audio = config.extra.get("generate_audio", True)
        if not self._api_key:
            self._logger.warning(
                "kling_provider_no_api_key",
                message="No FAL_KEY configured — provider disabled",
            )
            return  # stay uninitialised

        self._endpoint = (config.extra.get("endpoint") or self._endpoint).strip("/")
        self._model_name = config.model or self._model_name
        self._initialized = True
        self._logger.info(
            "kling_provider_initialized",
            model=self._model_name,
            endpoint=self._endpoint,
            cost_per_second=self._cost_per_second,
            generate_audio=self._generate_audio,
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise ProviderNotInitializedError(self.provider_name.value)

    async def generate_video(
        self,
        prompt: str,
        *,
        duration_seconds: float = 5.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        negative_prompt: str | None = None,
        seed: int | None = None,
        image: bytes | None = None,
        resolution: str | None = None,
        **kwargs: Any,
    ) -> bytes:
        """Generate a video and return only its downloaded bytes."""
        payload = await self.generate_video_with_resource(
            prompt,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            fps=fps,
            negative_prompt=negative_prompt,
            seed=seed,
            image=image,
            resolution=resolution,
            **kwargs,
        )
        return payload.video_bytes

    async def generate_video_with_resource(
        self,
        prompt: str,
        *,
        duration_seconds: float = 5.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        negative_prompt: str | None = None,
        seed: int | None = None,
        image: bytes | None = None,
        resolution: str | None = None,
        **kwargs: Any,
    ) -> VideoGenerationPayload:
        """Generate a video while retaining the accumulated clip bytes.

        ``remote_video`` carries the raw MP4 bytes — ``extend_video`` uses
        them to extract a last-frame chaining image and to prepend the
        existing footage onto the newly generated segment.
        """
        self._ensure_initialized()
        assert self._config is not None

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._generate_video_sync,
                    prompt,
                    duration_seconds,
                    width,
                    height,
                    negative_prompt,
                    image,
                ),
                timeout=self._config.request_timeout,
            )
        except asyncio.TimeoutError:
            raise AIProviderTimeoutError(self.provider_name.value, self._config.request_timeout)
        except AIProviderError:
            raise
        except Exception as exc:
            self._logger.error("kling_generate_error", error=str(exc))
            raise AIProviderError(self.provider_name.value, str(exc))

    async def extend_video(
        self,
        video: Any,
        prompt: str,
        *,
        duration_seconds: float = 7.0,
        width: int = 720,
        height: int = 1280,
        fps: int = 24,
        negative_prompt: str | None = None,
        **kwargs: Any,
    ) -> VideoGenerationPayload:
        """Continue an existing clip via last-frame image-to-video chaining.

        ``video`` is the accumulated MP4 bytes returned as ``remote_video``
        by the previous call.  The returned payload contains the previous
        footage concatenated with the newly generated segment, mirroring
        Veo's combined-extension contract.
        """
        self._ensure_initialized()
        assert self._config is not None

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._extend_video_sync,
                    video,
                    prompt,
                    duration_seconds,
                    width,
                    height,
                    negative_prompt,
                ),
                timeout=self._config.request_timeout,
            )
        except asyncio.TimeoutError:
            raise AIProviderTimeoutError(self.provider_name.value, self._config.request_timeout)
        except AIProviderError:
            raise
        except Exception as exc:
            self._logger.error("kling_extension_error", error=str(exc))
            raise AIProviderError(self.provider_name.value, str(exc))

    # ------------------------------------------------------------------
    # Synchronous fal.ai queue calls
    # ------------------------------------------------------------------
    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        resp = httpx.post(
            url,
            json=payload,
            headers={"Authorization": f"Key {self._api_key}"},
            timeout=60,
        )
        if resp.status_code >= 400:
            raise AIProviderError(
                self.provider_name.value,
                f"fal request failed ({resp.status_code}): {resp.text[:500]}",
            )
        return resp.json()

    def _get_json(self, url: str) -> dict[str, Any]:
        import httpx

        resp = httpx.get(
            url,
            headers={"Authorization": f"Key {self._api_key}"},
            timeout=60,
        )
        if resp.status_code >= 400:
            raise AIProviderError(
                self.provider_name.value,
                f"fal request failed ({resp.status_code}): {resp.text[:500]}",
            )
        return resp.json()

    def _submit_and_wait(self, endpoint: str, payload: dict[str, Any]) -> bytes:
        """Submit a fal queue job, poll until complete, download the MP4."""
        queue_url = f"{_FAL_QUEUE_BASE}/{endpoint}"
        submitted = self._post_json(queue_url, payload)
        request_id = submitted.get("request_id")
        if not request_id:
            raise AIProviderError(
                self.provider_name.value,
                f"fal submission returned no request_id: {submitted}",
            )
        # fal queue URLs are keyed by owner/app only — the full endpoint path
        # (e.g. .../kling-video/v3/standard/text-to-video/requests/...) 405s.
        # Prefer the URLs returned in the submit response; fall back to a
        # constructed owner/app path.
        owner_app = "/".join(endpoint.split("/")[:2])
        status_url = submitted.get("status_url") or (
            f"{_FAL_QUEUE_BASE}/{owner_app}/requests/{request_id}/status"
        )
        response_url = submitted.get("response_url") or (
            f"{_FAL_QUEUE_BASE}/{owner_app}/requests/{request_id}"
        )

        timeout = self._config.request_timeout if self._config else 600
        deadline = time.monotonic() + timeout
        poll_errors = 0
        while True:
            if time.monotonic() > deadline:
                raise AIProviderTimeoutError(self.provider_name.value, timeout)
            try:
                status = self._get_json(status_url)
            except AIProviderError:
                # A poll failure after a successful submit must NOT propagate
                # to the gateway's call-level retry — that would resubmit a
                # new (billed) generation.  fal requests persist in the queue,
                # so we keep polling the same request_id instead.
                poll_errors += 1
                if poll_errors >= 5:
                    raise
                time.sleep(_POLL_INTERVAL_SECONDS)
                continue
            state = status.get("status")
            if state == "COMPLETED":
                break
            if state in {"FAILED", "CANCELLED", "EXPIRED"}:
                raise AIProviderError(
                    self.provider_name.value,
                    f"fal request {request_id} ended as {state}: {status}",
                )
            time.sleep(_POLL_INTERVAL_SECONDS)

        # Result fetch + download also happen after billing — keep retrying
        # locally rather than letting a transient failure bubble up and cause
        # a gateway-level resubmit of a second paid generation.
        import httpx

        for _ in range(4):
            try:
                result = self._get_json(response_url)
                video_url = (result.get("video") or {}).get("url")
                if not video_url:
                    raise AIProviderError(
                        self.provider_name.value,
                        f"fal request {request_id} returned no video URL: {result}",
                    )
                video_resp = httpx.get(
                    video_url, timeout=300, follow_redirects=True
                )
                if video_resp.status_code != 200 or not video_resp.content:
                    raise AIProviderError(
                        self.provider_name.value,
                        f"Failed to download Kling video ({video_resp.status_code})",
                    )
                return video_resp.content
            except AIProviderError:
                time.sleep(_POLL_INTERVAL_SECONDS)
        raise AIProviderError(
            self.provider_name.value,
            f"fal request {request_id} completed but result fetch/download failed",
        )

    def _base_input(
        self,
        prompt: str,
        width: int,
        height: int,
        negative_prompt: str | None,
        *,
        image_to_video: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "generate_audio": self._generate_audio,
            "cfg_scale": 0.5,
        }
        # image-to-video derives the aspect ratio from the start image —
        # the parameter is only valid on the text-to-video endpoint.
        if not image_to_video:
            payload["aspect_ratio"] = "9:16" if height > width else "16:9"
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        return payload

    def _generate_video_sync(
        self,
        prompt: str,
        duration_seconds: float,
        width: int,
        height: int,
        negative_prompt: str | None,
        image: bytes | None,
    ) -> VideoGenerationPayload:
        duration = quantize_kling_duration(duration_seconds)
        payload = self._base_input(prompt, width, height, negative_prompt)
        payload["duration"] = str(duration)

        if image:
            endpoint = f"{self._endpoint}/image-to-video"
            payload = self._base_input(prompt, width, height, negative_prompt, image_to_video=True)
            payload["duration"] = str(duration)
            payload["start_image_url"] = (
                "data:image/png;base64," + base64.b64encode(image).decode()
            )
        else:
            endpoint = f"{self._endpoint}/text-to-video"

        self._logger.info(
            "kling_generate_started",
            model=self._model_name,
            endpoint=endpoint,
            duration_seconds=duration,
            prompt_chars=len(prompt),
        )
        data = self._submit_and_wait(endpoint, payload)
        self._logger.info(
            "kling_generate_completed",
            model=self._model_name,
            duration_seconds=duration,
            video_size_bytes=len(data),
        )
        return VideoGenerationPayload(video_bytes=data, remote_video=data)

    def _extend_video_sync(
        self,
        video: Any,
        prompt: str,
        duration_seconds: float,
        width: int,
        height: int,
        negative_prompt: str | None,
    ) -> VideoGenerationPayload:
        if not isinstance(video, (bytes, bytearray)):
            raise AIProviderError(
                self.provider_name.value,
                "Kling extension requires the accumulated video bytes",
            )
        duration = quantize_kling_duration(duration_seconds)
        last_frame = _last_frame_png(bytes(video))

        payload = self._base_input(prompt, width, height, negative_prompt, image_to_video=True)
        payload["duration"] = str(duration)
        payload["start_image_url"] = (
            "data:image/png;base64," + base64.b64encode(last_frame).decode()
        )
        endpoint = f"{self._endpoint}/image-to-video"

        self._logger.info(
            "kling_extension_started",
            model=self._model_name,
            endpoint=endpoint,
            extension_seconds=duration,
            prompt_chars=len(prompt),
        )
        new_clip = self._submit_and_wait(endpoint, payload)
        combined = _concat_mp4(bytes(video), new_clip)
        self._logger.info(
            "kling_extension_completed",
            model=self._model_name,
            extension_seconds=duration,
            video_size_bytes=len(combined),
        )
        return VideoGenerationPayload(video_bytes=combined, remote_video=combined)

    # ------------------------------------------------------------------
    # Cost + lifecycle
    # ------------------------------------------------------------------
    def calculate_cost(self, duration_seconds: float, resolution: str) -> float:
        """Calculate cost based on per-second pricing (audio-inclusive rate)."""
        billed = quantize_kling_duration(duration_seconds)
        return round(self._cost_per_second * billed, 6)

    def calculate_extension_cost(self, duration_seconds: float = 7.0) -> float:
        return round(self._cost_per_second * quantize_kling_duration(duration_seconds), 6)

    async def health_check(self) -> HealthStatus:
        if not self._initialized:
            return HealthStatus(
                healthy=False,
                provider=self.provider_name.value,
                details={"reason": "not initialized"},
            )
        return HealthStatus(
            healthy=True,
            provider=self.provider_name.value,
            details={"model": self._model_name, "endpoint": self._endpoint},
        )

    async def shutdown(self) -> None:
        self._initialized = False
        self._logger.info("kling_provider_shutdown")
