"""Unit tests for the rate-limit wait-and-retry wrapper."""

from __future__ import annotations

import pytest

from ytdl.services.pipeline.throttle import retry_on_rate_limit
from ytdl.shared.errors import RateLimitExceededError


def test_waits_the_hinted_window_then_succeeds() -> None:
    state = {"n": 0}
    slept: list[float] = []

    def call():
        state["n"] += 1
        if state["n"] < 3:
            raise RateLimitExceededError("cap reached; retry in ~48s to protect the account")
        return "ok"

    assert retry_on_rate_limit(call, sleep_fn=slept.append) == "ok"
    assert state["n"] == 3
    assert slept == [50.0, 50.0]  # parsed 48s + 2s margin, slept twice before success


def test_gives_up_after_max_waits() -> None:
    slept: list[float] = []

    def call():
        raise RateLimitExceededError("blocked")  # no hint → default wait

    with pytest.raises(RateLimitExceededError):
        retry_on_rate_limit(call, sleep_fn=slept.append, max_waits=2, default_wait=10.0)
    assert slept == [10.0, 10.0]
