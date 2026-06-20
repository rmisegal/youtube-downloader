"""RateLimiter: sliding-window request limiter plus concurrency tracking.

Limits are sourced from ``rate_limits.json`` -> ``rate_limits.services.youtube``
and passed in as a dict; nothing is hardcoded. Function-parameter defaults act
only as last-resort fallbacks when a key is absent (PRD section 6.3, Rule 11).

The time source is injected via ``time_fn`` so tests can drive a fake clock
without real sleeping. This class NEVER calls ``time.sleep``.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from typing import Any

# Fallback defaults only (used when a config key is missing).
_DEFAULT_RPM = 20
_DEFAULT_CONCURRENT_MAX = 2
_DEFAULT_BURST_SIZE = 5
_DEFAULT_BURST_WINDOW_S = 10
_RPM_WINDOW_SECONDS = 60.0


class RateLimiter:
    """Enforce per-minute and burst request limits over a sliding window.

    Two independent windows must both have room for a request to be allowed:

    * the rolling 60-second window (``requests_per_minute``), and
    * the rolling ``burst_window_seconds`` window (``burst_size``).

    Concurrency is tracked separately via :meth:`acquire` / :meth:`release`.
    """

    def __init__(
        self,
        limits: dict[str, Any] | None = None,
        time_fn: Callable[[], float] = time.monotonic,
        *,
        requests_per_minute: int = _DEFAULT_RPM,
        concurrent_max: int = _DEFAULT_CONCURRENT_MAX,
        burst_size: int = _DEFAULT_BURST_SIZE,
        burst_window_seconds: float = _DEFAULT_BURST_WINDOW_S,
    ) -> None:
        """Build a limiter from a config ``limits`` dict.

        Args:
            limits: Mapping with ``requests_per_minute``, ``concurrent_max``,
                ``burst_size`` and ``burst_window_seconds`` (from config).
            time_fn: Zero-arg monotonic clock; injected for testability.
            requests_per_minute: Fallback when absent from ``limits``.
            concurrent_max: Fallback when absent from ``limits``.
            burst_size: Fallback when absent from ``limits``.
            burst_window_seconds: Fallback when absent from ``limits``.
        """
        cfg = limits or {}
        self._rpm = int(cfg.get("requests_per_minute", requests_per_minute))
        self._concurrent_max = int(cfg.get("concurrent_max", concurrent_max))
        self._burst_size = int(cfg.get("burst_size", burst_size))
        self._burst_window = float(cfg.get("burst_window_seconds", burst_window_seconds))
        self._time_fn = time_fn

        self._events: deque[float] = deque()  # timestamps of granted requests
        self._active = 0

    def _prune(self, now: float) -> None:
        """Drop timestamps older than the longest tracked window."""
        horizon = now - max(_RPM_WINDOW_SECONDS, self._burst_window)
        while self._events and self._events[0] <= horizon:
            self._events.popleft()

    def _count_within(self, now: float, window: float) -> int:
        """Number of granted requests within ``window`` seconds of ``now``."""
        cutoff = now - window
        return sum(1 for ts in self._events if ts > cutoff)

    def allow(self) -> bool:
        """Try to consume one request slot.

        Returns ``True`` and records the request when both the per-minute and
        burst windows have room; otherwise returns ``False`` and records nothing.
        """
        now = self._time_fn()
        self._prune(now)
        if self._count_within(now, _RPM_WINDOW_SECONDS) >= self._rpm:
            return False
        if self._count_within(now, self._burst_window) >= self._burst_size:
            return False
        self._events.append(now)
        return True

    def wait_seconds(self) -> float:
        """Seconds until the next request would be allowed (``0.0`` if now)."""
        now = self._time_fn()
        self._prune(now)
        waits = []
        if self._count_within(now, _RPM_WINDOW_SECONDS) >= self._rpm:
            waits.append(self._slot_free_in(now, _RPM_WINDOW_SECONDS, self._rpm))
        if self._count_within(now, self._burst_window) >= self._burst_size:
            waits.append(self._slot_free_in(now, self._burst_window, self._burst_size))
        return max(waits) if waits else 0.0

    def _slot_free_in(self, now: float, window: float, limit: int) -> float:
        """Time until the oldest in-window event for ``limit`` expires."""
        in_window = [ts for ts in self._events if ts > now - window]
        # The (len - limit + 1)-th oldest event must leave the window.
        index = len(in_window) - limit
        target = in_window[max(index, 0)]
        return max((target + window) - now, 0.0)

    def acquire(self) -> bool:
        """Reserve one concurrency slot; ``False`` if at ``concurrent_max``."""
        if self._active >= self._concurrent_max:
            return False
        self._active += 1
        return True

    def release(self) -> None:
        """Release one concurrency slot (never drops below zero)."""
        if self._active > 0:
            self._active -= 1

    @property
    def active(self) -> int:
        """Current number of held concurrency slots."""
        return self._active
