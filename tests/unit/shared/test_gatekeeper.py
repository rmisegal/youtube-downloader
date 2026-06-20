"""Unit tests for ytdl.shared.gatekeeper.ApiGatekeeper.

The callable is mocked, ``sleep_fn`` is a no-op recorder, and the rate limiter /
queue are real in-memory objects. No network and no real sleeping occur.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from ytdl.shared.config import ConfigManager
from ytdl.shared.gatekeeper import ApiGatekeeper
from ytdl.shared.queue import DownloadQueue
from ytdl.shared.rate_limit import RateLimiter

YOUTUBE_LIMITS: dict = {
    "requests_per_minute": 20,
    "concurrent_max": 2,
    "burst_size": 5,
    "burst_window_seconds": 10,
}


class FakeClock:
    """A monotonic clock advanced only on demand."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now


class SleepRecorder:
    """A no-op sleep that records each requested duration."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _queue(max_depth: int = 100) -> DownloadQueue:
    cfg = ConfigManager(
        data={
            "version": "1.00",
            "queue": {"max_depth": max_depth, "overflow_strategy": "reject_oldest"},
        }
    )
    return DownloadQueue(cfg)


def _limiter(**overrides: object) -> RateLimiter:
    limits = {**YOUTUBE_LIMITS, **overrides}
    return RateLimiter(limits=limits, time_fn=FakeClock())


def _gatekeeper(limiter: RateLimiter, queue: DownloadQueue, **kw: Any) -> tuple[
    ApiGatekeeper, SleepRecorder
]:
    sleeper = SleepRecorder()
    gk = ApiGatekeeper(
        limiter, queue, sleep_fn=sleeper, max_retries=kw.pop("max_retries", 2),
        retry_after_seconds=kw.pop("retry_after_seconds", 30), **kw
    )
    return gk, sleeper


def test_happy_path_executes_once_and_returns() -> None:
    calls: list[tuple] = []

    def func(x: int) -> int:
        calls.append((x,))
        return x * 2

    gk, sleeper = _gatekeeper(_limiter(), _queue())
    result = gk.execute(func, 21)

    assert result == 42
    assert calls == [(21,)]
    assert sleeper.calls == []


def test_rate_limit_checked_before_call_enqueues_request() -> None:
    # requests_per_minute=0 -> allow() always denies; call must be enqueued.
    queue = _queue()
    gk, _ = _gatekeeper(_limiter(requests_per_minute=0), queue)

    def func() -> str:
        return "ok"

    result = gk.execute(func)

    assert result == "ok"  # rate-limited call proceeds, not an exception
    assert queue.depth == 1
    queued = queue.dequeue()
    assert queued["func"] == "func"


def test_overflow_path_enqueues_onto_queue() -> None:
    queue = _queue(max_depth=1)
    gk, _ = _gatekeeper(_limiter(requests_per_minute=0), queue)

    gk.execute(lambda: 1)
    gk.execute(lambda: 2)

    # Both rate-limited calls were enqueued; queue never raised on overflow.
    assert queue.depth == 1
    assert gk.get_queue_status()["is_full"] is True


def test_retry_on_transient_error_then_success() -> None:
    attempts = {"n": 0}

    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("transient")
        return "done"

    gk, sleeper = _gatekeeper(_limiter(), _queue(), max_retries=3, retry_after_seconds=30)
    result = gk.execute(flaky)

    assert result == "done"
    assert attempts["n"] == 3
    # Slept between the two failed attempts (2 backoffs), each retry_after_seconds.
    assert sleeper.calls == [30, 30]


def test_exhausting_retries_reraises() -> None:
    def always_fail() -> None:
        raise ValueError("boom")

    gk, sleeper = _gatekeeper(_limiter(), _queue(), max_retries=2, retry_after_seconds=5)

    with pytest.raises(ValueError, match="boom"):
        gk.execute(always_fail)

    # max_retries=2 -> 3 attempts -> 2 backoffs between them.
    assert sleeper.calls == [5, 5]


def test_each_call_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    gk, _ = _gatekeeper(_limiter(), _queue())

    def func() -> int:
        return 7

    with caplog.at_level(logging.INFO, logger="ytdl.shared.gatekeeper"):
        gk.execute(func)

    messages = [r.getMessage() for r in caplog.records]
    assert any("Calling func" in m for m in messages)
    assert any("succeeded" in m for m in messages)


def test_get_queue_status_reports_depth() -> None:
    queue = _queue(max_depth=5)
    gk, _ = _gatekeeper(_limiter(), queue)

    status = gk.get_queue_status()

    assert status == {"depth": 0, "max_depth": 5, "is_full": False}
