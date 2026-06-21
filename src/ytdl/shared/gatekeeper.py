"""ApiGatekeeper: the single choke point for throttled external (YouTube) calls.

Every network call is routed through :meth:`ApiGatekeeper.execute`, which:

* consults the :class:`~ytdl.shared.rate_limit.RateLimiter` before calling and,
  when no slot is currently available, enqueues a representation of the request
  onto the :class:`~ytdl.shared.queue.DownloadQueue` so overflow is *queued,
  never dropped or crashed* (PRD section 4.1, Rules 3 and 5);
* retries transient failures up to ``max_retries``, sleeping
  ``retry_after_seconds`` between attempts via an injected ``sleep_fn`` (so tests
  never really sleep);
* logs every call attempt and re-raises the last exception once retries are
  exhausted.

Retry settings come from ``rate_limits.json`` -> ``rate_limits.services.youtube``
and are passed in; named defaults are last-resort fallbacks only (Rule 11).
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from ytdl.shared.queue import DownloadQueue
from ytdl.shared.rate_limit import RateLimiter
from ytdl.shared.usage import UsageTracker

# Fallback-only defaults (used solely when a config key is absent).
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_AFTER_SECONDS = 30

_LOGGER = logging.getLogger(__name__)


class ApiGatekeeper:
    """Centralized rate-checked, retrying, logged executor for API calls."""

    def __init__(
        self,
        rate_limiter: RateLimiter,
        queue: DownloadQueue,
        *,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        retry_after_seconds: float = _DEFAULT_RETRY_AFTER_SECONDS,
        sleep_fn: Callable[[float], None] = time.sleep,
        logger: logging.Logger | None = None,
        usage: UsageTracker | None = None,
    ) -> None:
        """Build a gatekeeper.

        Args:
            rate_limiter: Limiter consulted before every call.
            queue: Queue that absorbs rate-limited overflow requests.
            max_retries: Max retry attempts on transient errors (from config).
            retry_after_seconds: Backoff between retries (from config).
            sleep_fn: Injectable sleep; default :func:`time.sleep`.
            logger: Optional logger; defaults to the module logger.
        """
        self._rate_limiter = rate_limiter
        self._queue = queue
        self._max_retries = int(max_retries)
        self._retry_after = float(retry_after_seconds)
        self._sleep_fn = sleep_fn
        self._log = logger or _LOGGER
        self._usage = usage
        self._check_lock = threading.Lock()  # serialize the rate/quota check only

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run ``func`` under rate control with retry/backoff and logging.

        Consults the rate limiter first; if no slot is free the request is
        enqueued (never dropped). Then calls ``func``, retrying transient
        failures up to ``max_retries`` with ``retry_after_seconds`` backoff.
        Returns the result on success; re-raises the last error if all
        attempts fail.
        """
        name = getattr(func, "__name__", repr(func))
        # The quota/rate CHECK mutates shared state, so it is serialized by a lock
        # (cheap) — but ``func`` itself (the slow network call) runs OUTSIDE the lock,
        # so parallel downloads run concurrently. Quota raises outside the retry loop
        # so a quota stop is never retried into a YouTube ban.
        with self._check_lock:
            if self._usage is not None:
                self._usage.reserve()
            allowed = self._rate_limiter.allow()
            if not allowed:
                self._log.info("Rate limit reached; queuing call %s", name)
                self._queue.enqueue(self._request(func, args, kwargs))
        return self._run_with_retries(func, name, args, kwargs)

    def _run_with_retries(
        self,
        func: Callable[..., Any],
        name: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        """Invoke ``func`` with retry/backoff; re-raise after exhaustion."""
        attempts = self._max_retries + 1
        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            self._log.info("Calling %s (attempt %d/%d)", name, attempt, attempts)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - transient retry boundary
                last_exc = exc
                self._log.warning("Call %s failed on attempt %d: %s", name, attempt, exc)
                if attempt < attempts:
                    self._sleep_fn(self._retry_after)
                continue
            self._log.info("Call %s succeeded on attempt %d", name, attempt)
            return result
        assert last_exc is not None  # noqa: S101 - loop guarantees this
        raise last_exc

    @staticmethod
    def _request(
        func: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a serializable-ish representation of a deferred request."""
        return {
            "func": getattr(func, "__name__", repr(func)),
            "args": args,
            "kwargs": kwargs,
        }

    def get_queue_status(self) -> dict[str, Any]:
        """Return current queue depth and capacity information."""
        return {
            "depth": self._queue.depth,
            "max_depth": self._queue.max_depth,
            "is_full": self._queue.is_full(),
        }
