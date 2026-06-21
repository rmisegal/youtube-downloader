"""Wait-and-retry around the rate-limit gatekeeper for the long pipeline loops.

The gatekeeper RAISES ``RateLimitExceededError`` to protect the account when the
per-minute cap is hit. A 70+ search/download pipeline expects this repeatedly, so the
MATCH/FETCH loops wrap each call: on a rate-limit stop they sleep the suggested window
and retry (the stage caches progress, so nothing is lost). ``sleep_fn`` is injectable
so tests never really sleep.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

from ytdl.shared.errors import RateLimitExceededError

_RETRY_RE = re.compile(r"retry in ~?(\d+)")


def _wait_seconds(exc: Exception, default: float) -> float:
    """Seconds to wait — parsed from the gatekeeper message, else ``default``."""
    match = _RETRY_RE.search(str(exc))
    return float(match.group(1)) + 2.0 if match else default


def retry_on_rate_limit(
    call: Callable[[], Any], *, sleep_fn: Callable[[float], None] = time.sleep,
    max_waits: int = 40, default_wait: float = 35.0,
) -> Any:
    """Run ``call``; on a rate-limit stop, sleep + retry (up to ``max_waits`` times)."""
    for _ in range(max_waits):
        try:
            return call()
        except RateLimitExceededError as exc:
            sleep_fn(_wait_seconds(exc, default_wait))
    return call()  # final attempt — let any error propagate
