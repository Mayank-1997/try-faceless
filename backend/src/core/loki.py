"""Grafana Cloud Loki log shipping handler.

Buffers log records and pushes them to Loki's HTTP push endpoint
(``POST {LOKI_URL}/loki/api/v1/push``) on a background thread so logging
never blocks the request/workflow path.  Activated via::

    LOKI_ENABLED=true
    LOKI_URL=https://logs-prod-us-central1.grafana.net
    LOKI_USER=<grafana cloud user/instance id>
    LOKI_API_KEY=<grafana cloud API key (logs:write)>
"""

from __future__ import annotations

import atexit
import base64
import json
import logging
import re
import threading
import time
from queue import Empty, Queue

import httpx

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class LokiHandler(logging.Handler):
    """Stdlib ``logging.Handler`` that ships records to Grafana Cloud Loki.

    Records are queued and flushed in batches by a daemon thread, so a
    slow or down Loki endpoint never blocks the application.
    """

    _PUSH_PATH = "/loki/api/v1/push"

    def __init__(
        self,
        *,
        url: str,
        user: str,
        api_key: str,
        labels: dict[str, str],
        push_interval: float = 5.0,
        batch_size: int = 500,
    ) -> None:
        super().__init__()
        self._endpoint = f"{url.rstrip('/')}{self._PUSH_PATH}"
        self._auth = base64.b64encode(f"{user}:{api_key}".encode()).decode()
        self._labels = labels
        self._batch_size = batch_size
        self._push_interval = push_interval
        self._queue: Queue[tuple[str, float]] = Queue(maxsize=10_000)
        self._stop = threading.Event()
        self._warned = False
        self._flusher = threading.Thread(
            target=self._flush_loop, name="loki-flush", daemon=True
        )
        self._flusher.start()
        atexit.register(self.close)

    def emit(self, record: logging.LogRecord) -> None:
        """Enqueue a log record — drops silently if the buffer is full."""
        try:
            line = _ANSI_RE.sub("", self.format(record))
            self._queue.put_nowait((line, record.created))
        except Exception:
            self.handleError(record)

    def _flush_loop(self) -> None:
        """Background thread: flush buffered entries every interval."""
        while not self._stop.is_set():
            self._stop.wait(self._push_interval)
            self._flush()
        self._flush()  # final flush on shutdown

    def _flush(self) -> None:
        entries: list[tuple[str, float]] = []
        while len(entries) < self._batch_size:
            try:
                entries.append(self._queue.get_nowait())
            except Empty:
                break
        if not entries:
            return

        # Loki groups values by label stream; group by (level)
        streams: dict[str, list[list[str]]] = {}
        for line, ts in entries:
            ns = str(int(ts * 1e9))
            streams.setdefault("all", []).append([ns, line])

        body = {
            "streams": [
                {"stream": self._labels, "values": values}
                for values in streams.values()
            ]
        }
        try:
            resp = httpx.post(
                self._endpoint,
                content=json.dumps(body),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {self._auth}",
                },
                timeout=15,
            )
            if resp.status_code >= 400 and not self._warned:
                self._warned = True
                import sys
                sys.stderr.write(
                    f"[loki] push failed ({resp.status_code}): {resp.text[:300]}\n"
                )
        except Exception as exc:
            if not self._warned:
                self._warned = True
                import sys
                sys.stderr.write(f"[loki] push error: {exc}\n")

    def close(self) -> None:
        self._stop.set()
        super().close()


def install_loki_handler(settings) -> bool:
    """Attach a ``LokiHandler`` to the root logger if configured.

    Returns ``True`` if the handler was installed.
    """
    loki = getattr(settings, "loki", None)
    if not loki or not loki.enabled or not (loki.url and loki.user and loki.api_key):
        return False

    handler = LokiHandler(
        url=loki.url,
        user=loki.user,
        api_key=loki.api_key,
        labels={
            "app": settings.app_name.replace(" ", "_").lower(),
            "env": settings.environment,
        },
        push_interval=loki.push_interval_seconds,
        batch_size=loki.batch_size,
    )
    handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(handler)
    return True
