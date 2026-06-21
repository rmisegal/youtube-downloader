"""Pace the long pipeline loops under the rate-limit gatekeeper (glb Rule 5).

The gatekeeper RAISES ``RateLimitExceededError`` when the per-minute cap is hit. A 70+
search/download pipeline expects this constantly, so MATCH/FETCH wrap each call and,
on a stop, sleep a SHORT interval and retry. A short wait (not the full ~minute the
message suggests) matters: the sliding window frees a slot every few seconds, so a
brief retry paces the loop at the allowed rate instead of stalling ~35s each time. The
stage caches progress, so nothing is lost; ``sleep_fn`` is injectable for tests.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from ytdl.shared.errors import RateLimitExceededError

# Just over the steady-state slot interval (10/min ≈ one slot every 6s) so a blocked
# call retries soon after a slot frees rather than waiting the whole window.
_WAIT_SECONDS = 7.0
# Enough retries to outlast a fully-saturated window (~a minute) at the start of a stage.
_MAX_WAITS = 240


def retry_on_rate_limit(
    call: Callable[[], Any], *, sleep_fn: Callable[[float], None] = time.sleep,
    wait_seconds: float = _WAIT_SECONDS, max_waits: int = _MAX_WAITS,
) -> Any:
    """Run ``call``; on a rate-limit stop, sleep ``wait_seconds`` and retry."""
    for _ in range(max_waits):
        try:
            return call()
        except RateLimitExceededError:
            sleep_fn(wait_seconds)
    return call()  # final attempt — let any error propagate
