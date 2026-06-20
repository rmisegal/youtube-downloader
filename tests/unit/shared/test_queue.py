"""Unit tests for ytdl.shared.queue.DownloadQueue.

No network and no real sleeping: the queue is pure in-memory.
"""

from __future__ import annotations

from ytdl.shared.config import ConfigManager
from ytdl.shared.queue import DownloadQueue


def _config(**queue_overrides: object) -> ConfigManager:
    """Build a ConfigManager whose ``queue`` block uses the given overrides."""
    queue = {
        "max_depth": 100,
        "drain_interval_seconds": 1,
        "timeout_seconds": 300,
        "overflow_strategy": "reject_oldest",
    }
    queue.update(queue_overrides)
    return ConfigManager(data={"version": "1.00", "queue": queue})


def test_config_values_sourced_from_config() -> None:
    cfg = _config(max_depth=7, overflow_strategy="reject_new")
    q = DownloadQueue(cfg)

    assert q.max_depth == 7
    assert q.overflow_strategy == "reject_new"
    assert q.drain_interval_seconds == 1
    assert q.timeout_seconds == 300


def test_fifo_ordering_preserved() -> None:
    q = DownloadQueue(_config(max_depth=10))

    for item in ("a", "b", "c"):
        q.enqueue(item)

    assert q.dequeue() == "a"
    assert q.dequeue() == "b"
    assert q.dequeue() == "c"


def test_len_and_full_state() -> None:
    q = DownloadQueue(_config(max_depth=2))

    assert len(q) == 0
    assert not q.is_full()

    q.enqueue("x")
    assert len(q) == 1

    q.enqueue("y")
    assert len(q) == 2
    assert q.is_full()
    assert q.depth == 2


def test_empty_dequeue_returns_none() -> None:
    q = DownloadQueue(_config())

    assert q.dequeue() is None
    assert len(q) == 0


def test_overflow_reject_oldest_drops_oldest_and_accepts_new() -> None:
    q = DownloadQueue(_config(max_depth=2, overflow_strategy="reject_oldest"))

    q.enqueue("a")
    q.enqueue("b")
    accepted = q.enqueue("c")  # overflow: drop "a", keep "b", "c"

    assert accepted is True
    assert len(q) == 2
    assert q.dequeue() == "b"
    assert q.dequeue() == "c"


def test_overflow_reject_new_rejects_incoming_item() -> None:
    q = DownloadQueue(_config(max_depth=2, overflow_strategy="reject_new"))

    q.enqueue("a")
    q.enqueue("b")
    accepted = q.enqueue("c")  # overflow: incoming rejected

    assert accepted is False
    assert len(q) == 2
    assert q.dequeue() == "a"
    assert q.dequeue() == "b"


def test_overflow_unknown_strategy_treated_as_reject_new() -> None:
    q = DownloadQueue(_config(max_depth=1, overflow_strategy="mystery"))

    q.enqueue("a")
    accepted = q.enqueue("b")

    assert accepted is False
    assert len(q) == 1
    assert q.dequeue() == "a"


def test_overflow_never_raises() -> None:
    q = DownloadQueue(_config(max_depth=1, overflow_strategy="reject_oldest"))

    # Many enqueues over capacity must never raise.
    for item in range(100):
        q.enqueue(item)

    assert len(q) == 1


def test_drain_processes_every_item_once_in_order() -> None:
    q = DownloadQueue(_config(max_depth=10))
    for item in ("a", "b", "c"):
        q.enqueue(item)

    seen: list[str] = []
    count = q.drain(seen.append)

    assert seen == ["a", "b", "c"]
    assert count == 3
    assert len(q) == 0


def test_drain_empty_queue_is_noop() -> None:
    q = DownloadQueue(_config())

    seen: list[object] = []
    count = q.drain(seen.append)

    assert seen == []
    assert count == 0
