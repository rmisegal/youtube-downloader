"""Unit tests for ``ApiGatekeeper`` persistent-quota (``usage``) integration.

A permissive RateLimiter (``allow()`` always True) and a real in-memory
DownloadQueue are used; ``usage.reserve`` is a mock so we control quota outcome.
No network, no sleeping.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ytdl.shared.config import ConfigManager
from ytdl.shared.errors import RateLimitExceededError
from ytdl.shared.gatekeeper import ApiGatekeeper
from ytdl.shared.queue import DownloadQueue


def _queue() -> DownloadQueue:
    cfg = ConfigManager(
        data={
            "version": "1.00",
            "queue": {"max_depth": 100, "overflow_strategy": "reject_oldest"},
        }
    )
    return DownloadQueue(cfg)


def _permissive_limiter() -> MagicMock:
    limiter = MagicMock(name="RateLimiter")
    limiter.allow.return_value = True
    return limiter


def _gatekeeper(usage: MagicMock) -> ApiGatekeeper:
    return ApiGatekeeper(
        _permissive_limiter(), _queue(), usage=usage, sleep_fn=lambda *_: None
    )


def test_reserve_raise_propagates_without_calling_func() -> None:
    usage = MagicMock(name="UsageTracker")
    usage.reserve.side_effect = RateLimitExceededError("quota hit")
    func = MagicMock(name="func")
    gk = _gatekeeper(usage)

    with pytest.raises(RateLimitExceededError, match="quota hit"):
        gk.execute(func)

    func.assert_not_called()
    usage.reserve.assert_called_once()


def test_reserve_called_once_then_func_runs() -> None:
    usage = MagicMock(name="UsageTracker")
    usage.reserve.return_value = None
    func = MagicMock(name="func", return_value="ok")
    gk = _gatekeeper(usage)

    assert gk.execute(func, 1, k=2) == "ok"

    usage.reserve.assert_called_once()
    func.assert_called_once_with(1, k=2)


def test_no_usage_means_no_reserve_and_func_runs() -> None:
    func = MagicMock(name="func", return_value=7)
    gk = ApiGatekeeper(
        _permissive_limiter(), _queue(), usage=None, sleep_fn=lambda *_: None
    )
    assert gk.execute(func) == 7
