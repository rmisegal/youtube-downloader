"""Unit tests for the Safe-Race concurrency building block (pool + watchdog + mutex)."""

from __future__ import annotations

import threading
import time

from ytdl.shared.concurrency import OperationWatchdog, monitored_worker, run_pool


def test_run_pool_processes_all_items_concurrently() -> None:
    seen = set()
    lock = threading.Lock()

    def work(item, heartbeat):  # noqa: ANN001
        heartbeat(f"item-{item}")
        with lock:
            seen.add(item)
        return item * 2

    out = run_pool(range(10), work, workers=4, op_name="t", timeout=30.0)
    assert sorted(out) == [i * 2 for i in range(10)]
    assert seen == set(range(10))


def test_run_pool_empty_is_noop() -> None:
    assert run_pool([], lambda i, h: i, workers=4, op_name="t") == []


def test_monitored_worker_registers_and_deregisters() -> None:
    dog = OperationWatchdog("t", timeout=30.0)
    assert dog.active == 0
    with monitored_worker(dog, "w") as beat:
        assert dog.active == 1
        beat("midway")  # heartbeat updates state without error
    assert dog.active == 0  # deregistered on exit (RAII)


def test_watchdog_flags_a_stalled_worker() -> None:
    dog = OperationWatchdog("t", timeout=0.0)  # anything older than 'now' is stuck
    dog.started(123, "frozen")
    time.sleep(0.01)
    stuck = dog._scan()
    assert [i.name for i in stuck] == ["frozen"] and dog.stuck == 1


def test_watchdog_healthy_worker_not_flagged() -> None:
    dog = OperationWatchdog("t", timeout=60.0)
    dog.started(1, "ok")
    dog.beat(1, "alive")
    assert dog._scan() == [] and dog.stuck == 0
