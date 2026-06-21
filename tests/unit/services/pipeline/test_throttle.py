"""Unit tests for the rate-limit wait-and-retry wrapper."""

from __future__ import annotations

import pytest

from ytdl.services.pipeline.throttle import retry_on_rate_limit
from ytdl.shared.errors import RateLimitExceededError


def test_short_waits_then_succeeds() -> None:
    state = {"n": 0}
    slept: list[float] = []

    def call():
        state["n"] += 1
        if state["n"] < 3:
            raise RateLimitExceededError("cap reached; retry in ~48s to protect the account")
        return "ok"

    assert retry_on_rate_limit(call, sleep_fn=slept.append, wait_seconds=7.0) == "ok"
    assert state["n"] == 3
    assert slept == [7.0, 7.0]  # short waits (paces at the allowed rate), not the full window


def test_gives_up_after_max_waits() -> None:
    slept: list[float] = []

    def call():
        raise RateLimitExceededError("blocked")

    with pytest.raises(RateLimitExceededError):
        retry_on_rate_limit(call, sleep_fn=slept.append, max_waits=2, wait_seconds=5.0)
    assert slept == [5.0, 5.0]
