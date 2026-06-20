"""Unit tests for ytdl.shared.usage.UsageTracker.

Uses ``tmp_path`` for the on-disk ledger and a mutable fake clock so no real
time passes and no network is touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ytdl.shared.errors import RateLimitExceededError
from ytdl.shared.usage import UsageTracker


class FakeClock:
    """An epoch-seconds clock whose value advances only when told to."""

    def __init__(self, start: float = 1_000_000.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    return tmp_path / "ledger" / "usage.json"


def test_per_minute_cap_blocks_fourth_call(clock: FakeClock, state_path: Path) -> None:
    tracker = UsageTracker({"requests_per_minute": 3}, state_path, time_fn=clock)

    tracker.reserve()
    tracker.reserve()
    tracker.reserve()
    with pytest.raises(RateLimitExceededError):
        tracker.reserve()


def test_window_slides_after_sixty_seconds(clock: FakeClock, state_path: Path) -> None:
    tracker = UsageTracker({"requests_per_minute": 1}, state_path, time_fn=clock)

    tracker.reserve()
    with pytest.raises(RateLimitExceededError):
        tracker.reserve()

    clock.advance(61)
    tracker.reserve()  # window slid; oldest timestamp expired


def test_persistence_across_instances(clock: FakeClock, state_path: Path) -> None:
    first = UsageTracker({"requests_per_minute": 2}, state_path, time_fn=clock)
    first.reserve()
    first.reserve()

    # A brand-new instance reads the same ledger and still enforces the cap.
    second = UsageTracker({"requests_per_minute": 2}, state_path, time_fn=clock)
    with pytest.raises(RateLimitExceededError):
        second.reserve()


def test_no_caps_never_raises(clock: FakeClock, state_path: Path) -> None:
    tracker = UsageTracker({}, state_path, time_fn=clock)
    for _ in range(100):
        tracker.reserve()


def test_non_positive_caps_are_ignored(clock: FakeClock, state_path: Path) -> None:
    tracker = UsageTracker(
        {"requests_per_minute": 0, "requests_per_hour": None},
        state_path,
        time_fn=clock,
    )
    for _ in range(50):
        tracker.reserve()


def test_corrupt_state_treated_as_empty(clock: FakeClock, state_path: Path) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{ this is not valid json", encoding="utf-8")

    tracker = UsageTracker({"requests_per_minute": 2}, state_path, time_fn=clock)
    tracker.reserve()  # must not crash; corrupt ledger starts empty
    tracker.reserve()
    with pytest.raises(RateLimitExceededError):
        tracker.reserve()


def test_multiple_windows_enforced_together(clock: FakeClock, state_path: Path) -> None:
    # Minute cap is generous; the per-day cap of 2 is the binding limit.
    tracker = UsageTracker(
        {"requests_per_minute": 100, "requests_per_day": 2},
        state_path,
        time_fn=clock,
    )

    tracker.reserve()
    tracker.reserve()
    with pytest.raises(RateLimitExceededError) as excinfo:
        tracker.reserve()
    assert "requests_per_day" in str(excinfo.value)


def test_counts_reports_per_window_totals(clock: FakeClock, state_path: Path) -> None:
    tracker = UsageTracker(
        {"requests_per_minute": 5, "requests_per_day": 5},
        state_path,
        time_fn=clock,
    )
    tracker.reserve()
    tracker.reserve()

    counts = tracker.counts()
    assert counts == {"requests_per_minute": 2, "requests_per_day": 2}


def test_reset_hint_present_in_message(clock: FakeClock, state_path: Path) -> None:
    tracker = UsageTracker({"requests_per_minute": 1}, state_path, time_fn=clock)
    tracker.reserve()
    clock.advance(20)
    with pytest.raises(RateLimitExceededError) as excinfo:
        tracker.reserve()
    msg = str(excinfo.value)
    assert "1/1" in msg
    assert "~40s" in msg  # 60s window, used at t=0, now t=20 -> 40s to reset
