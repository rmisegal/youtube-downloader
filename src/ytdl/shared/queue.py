"""DownloadQueue: an in-memory FIFO queue with configurable overflow handling.

All tunables (``max_depth``, ``overflow_strategy``, ``drain_interval_seconds``,
``timeout_seconds``) come from ``rate_limits.json`` -> ``queue`` via the passed-in
:class:`~ytdl.shared.config.ConfigManager`. The named defaults are last-resort
fallbacks only, never the source of business values.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Any

from ytdl.shared.config import ConfigManager

# Fallback-only defaults (used solely when a config key is absent).
_DEFAULT_MAX_DEPTH = 100
_DEFAULT_DRAIN_INTERVAL = 1
_DEFAULT_TIMEOUT = 300
_DEFAULT_OVERFLOW_STRATEGY = "reject_oldest"

# Overflow strategy names (true constants, not tunables).
_REJECT_OLDEST = "reject_oldest"


class DownloadQueue:
    """A FIFO queue bounded by ``max_depth`` with a configurable overflow policy.

    Overflow is always handled gracefully (the queue never raises on a full
    enqueue):

    * ``"reject_oldest"`` drops the oldest queued item to make room for the new
      one (the new item is accepted).
    * any other strategy (including ``"reject_new"`` or an unknown value)
      rejects the incoming item, leaving the queue unchanged.
    """

    def __init__(self, config: ConfigManager) -> None:
        """Read queue settings from ``config`` (``queue.*`` keys)."""
        self.max_depth: int = config.get("queue.max_depth", _DEFAULT_MAX_DEPTH)
        self.overflow_strategy: str = config.get(
            "queue.overflow_strategy", _DEFAULT_OVERFLOW_STRATEGY
        )
        self.drain_interval_seconds: int = config.get(
            "queue.drain_interval_seconds", _DEFAULT_DRAIN_INTERVAL
        )
        self.timeout_seconds: int = config.get(
            "queue.timeout_seconds", _DEFAULT_TIMEOUT
        )
        self._items: deque[Any] = deque()

    def enqueue(self, item: Any) -> bool:
        """Add ``item`` to the back of the queue, applying the overflow policy.

        Returns ``True`` if the item ends up queued, ``False`` if it was
        rejected. Never raises on overflow.
        """
        if not self.is_full():
            self._items.append(item)
            return True
        if self.overflow_strategy == _REJECT_OLDEST:
            self._items.popleft()
            self._items.append(item)
            return True
        # reject_new / unknown strategies: drop the incoming item.
        return False

    def dequeue(self) -> Any:
        """Remove and return the oldest item, or ``None`` when empty."""
        if not self._items:
            return None
        return self._items.popleft()

    def drain(self, handler: Callable[[Any], Any]) -> int:
        """Pass every queued item, oldest first, to ``handler``.

        Drains the queue completely and returns the number of items processed.
        """
        processed = 0
        while self._items:
            handler(self._items.popleft())
            processed += 1
        return processed

    @property
    def depth(self) -> int:
        """The current number of queued items."""
        return len(self._items)

    def is_full(self) -> bool:
        """Whether the queue has reached ``max_depth``."""
        return len(self._items) >= self.max_depth

    def __len__(self) -> int:
        """The current number of queued items."""
        return len(self._items)
