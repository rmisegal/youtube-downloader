"""Unit tests for ytdl.shared.rate_limit.RateLimiter.

Uses a controllable fake clock so no real time passes and no network is touched.
"""

from __future__ import annotations

import pytest

from ytdl.shared.config import ConfigManager
from ytdl.shared.rate_limit import RateLimiter

# Limits mirroring config/rate_limits.json -> rate_limits.services.youtube.
YOUTUBE_LIMITS: dict = {
    "requests_per_minute": 20,
    "concurrent_max": 2,
    "burst_size": 5,
    "burst_window_seconds": 10,
}


class FakeClock:
    """A monotonic clock whose value advances only when told to."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def _limiter(clock: FakeClock, **overrides: object) -> RateLimiter:
    limits = {**YOUTUBE_LIMITS, **overrides}
    return RateLimiter(limits=limits, time_fn=clock)


def test_allows_up_to_rpm_then_blocks(clock: FakeClock) -> None:
    # Big burst window so only requests_per_minute is the binding limit.
    limiter = _limiter(clock, requests_per_minute=3, burst_size=999, burst_window_seconds=999)

    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is True
    # 4th within the same minute is blocked.
    assert limiter.allow() is False


def test_rpm_slot_frees_after_window(clock: FakeClock) -> None:
    limiter = _limiter(clock, requests_per_minute=2, burst_size=999, burst_window_seconds=999)

    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False

    # Advance past the 60s sliding window; oldest entries expire.
    clock.advance(61)
    assert limiter.allow() is True


def test_limits_are_read_from_config_not_hardcoded(clock: FakeClock) -> None:
    strict = _limiter(clock, requests_per_minute=1, burst_size=999, burst_window_seconds=999)
    loose = FakeClock()
    loose_limiter = RateLimiter(
        limits={**YOUTUBE_LIMITS, "requests_per_minute": 5,
                "burst_size": 999, "burst_window_seconds": 999},
        time_fn=loose,
    )

    assert strict.allow() is True
    assert strict.allow() is False  # rpm == 1

    for _ in range(5):
        assert loose_limiter.allow() is True
    assert loose_limiter.allow() is False  # rpm == 5


def test_burst_size_within_burst_window(clock: FakeClock) -> None:
    # rpm high so burst is the binding limit: 3 requests / 5 seconds.
    limiter = _limiter(clock, requests_per_minute=999, burst_size=3, burst_window_seconds=5)

    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is True
    # 4th inside the 5s burst window is blocked.
    assert limiter.allow() is False

    # Move just past the burst window; burst budget refreshes.
    clock.advance(5.1)
    assert limiter.allow() is True


def test_burst_partial_window_expiry(clock: FakeClock) -> None:
    limiter = _limiter(clock, requests_per_minute=999, burst_size=2, burst_window_seconds=10)

    assert limiter.allow() is True  # t=0
    clock.advance(4)
    assert limiter.allow() is True  # t=4
    assert limiter.allow() is False  # burst full

    clock.advance(6.1)  # t=10.1: the t=0 entry left the window, t=4 remains
    assert limiter.allow() is True
    assert limiter.allow() is False


def test_wait_seconds_zero_when_slot_available(clock: FakeClock) -> None:
    limiter = _limiter(clock, requests_per_minute=2, burst_size=999, burst_window_seconds=999)

    assert limiter.wait_seconds() == 0.0
    limiter.allow()
    assert limiter.wait_seconds() == 0.0


def test_wait_seconds_reports_time_until_next_slot(clock: FakeClock) -> None:
    limiter = _limiter(clock, requests_per_minute=1, burst_size=999, burst_window_seconds=999)

    assert limiter.allow() is True
    clock.advance(20)
    # One rpm slot used at t=0; it frees 60s later -> 40s remaining at t=20.
    assert limiter.wait_seconds() == pytest.approx(40.0)


def test_wait_seconds_reflects_burst_limit(clock: FakeClock) -> None:
    limiter = _limiter(clock, requests_per_minute=999, burst_size=1, burst_window_seconds=10)

    assert limiter.allow() is True
    clock.advance(3)
    # Burst slot used at t=0 frees at t=10 -> 7s remaining at t=3.
    assert limiter.wait_seconds() == pytest.approx(7.0)


def test_concurrency_acquire_and_release(clock: FakeClock) -> None:
    limiter = _limiter(clock, concurrent_max=2)

    assert limiter.acquire() is True
    assert limiter.acquire() is True
    assert limiter.acquire() is False  # at concurrent_max

    limiter.release()
    assert limiter.acquire() is True


def test_release_does_not_go_negative(clock: FakeClock) -> None:
    limiter = _limiter(clock, concurrent_max=1)

    limiter.release()  # nothing acquired; must be a no-op
    assert limiter.acquire() is True
    assert limiter.acquire() is False


def test_defaults_used_when_limit_keys_absent(clock: FakeClock) -> None:
    # Empty limits dict -> fallback defaults apply; allow() still works.
    limiter = RateLimiter(limits={}, time_fn=clock)

    assert limiter.allow() is True


def test_constructed_from_config_manager() -> None:
    cfg = ConfigManager(
        data={
            "version": "1.00",
            "rate_limits": {"services": {"youtube": dict(YOUTUBE_LIMITS)}},
        }
    )
    clock = FakeClock()
    limits = cfg.get("rate_limits.services.youtube")
    limiter = RateLimiter(limits=limits, time_fn=clock)

    assert limiter.allow() is True
