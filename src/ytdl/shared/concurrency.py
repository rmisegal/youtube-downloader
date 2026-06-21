"""Thread-safety building block: a bounded worker pool with a deadlock watchdog.

Adapted from Dr. Segal's Safe-Race concurrency SDK (``rmi-reviews/src/shared/threading``):
a :class:`ThreadPoolExecutor` BOUNDS concurrency (semaphore-like), an
:class:`OperationWatchdog` detects hung/deadlocked workers via heartbeats, and ALL
shared state is guarded by a single ``Lock`` (mutex). Deadlock is avoided by the
four-conditions rule — one lock per resource, held only briefly around state mutation
(never around the slow work) and never nested — so there is no circular wait.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

_LOG = logging.getLogger("ytdl.concurrency")


@dataclass
class _ThreadInfo:
    name: str
    last_beat: float
    checkpoint: str = "started"


class OperationWatchdog:
    """Heartbeat-based deadlock/hang detector for one multi-threaded operation."""

    def __init__(self, op_name: str, *, timeout: float = 180.0, interval: float = 5.0) -> None:
        self._op = op_name
        self._timeout = timeout
        self._interval = interval
        self._threads: dict[int, _ThreadInfo] = {}
        self._lock = threading.Lock()  # the ONE mutex guarding all shared state
        self._stop = threading.Event()
        self._monitor: threading.Thread | None = None
        self.stuck = 0

    def start(self) -> None:
        self._stop.clear()
        self._monitor = threading.Thread(target=self._loop, daemon=True, name=f"watchdog-{self._op}")
        self._monitor.start()

    def stop(self) -> None:
        self._stop.set()
        if self._monitor:
            self._monitor.join(timeout=2.0)

    def started(self, tid: int, name: str) -> None:
        with self._lock:
            self._threads[tid] = _ThreadInfo(name, time.time())

    def beat(self, tid: int, checkpoint: str = "working") -> None:
        with self._lock:
            info = self._threads.get(tid)
            if info:
                info.last_beat = time.time()
                info.checkpoint = checkpoint

    def finished(self, tid: int) -> None:
        with self._lock:
            self._threads.pop(tid, None)

    @property
    def active(self) -> int:
        with self._lock:
            return len(self._threads)

    def _scan(self) -> list[_ThreadInfo]:
        """Return (and log) workers with no heartbeat within the timeout."""
        now = time.time()
        with self._lock:
            stuck = [i for i in self._threads.values() if now - i.last_beat > self._timeout]
        for info in stuck:
            self.stuck += 1
            _LOG.error("DEADLOCK/hang [%s]: %s stuck at '%s' for %.0fs",
                       self._op, info.name, info.checkpoint, now - info.last_beat)
        return stuck

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            self._scan()


@contextmanager
def monitored_worker(watchdog: OperationWatchdog, name: str):
    """Register a worker, yield a heartbeat fn, and deregister on exit (RAII)."""
    tid = threading.get_ident()
    watchdog.started(tid, name)
    try:
        yield lambda checkpoint="working": watchdog.beat(tid, checkpoint)
    finally:
        watchdog.finished(tid)


def run_pool(
    items: Iterable[Any], work: Callable[[Any, Callable[..., None]], Any], *,
    workers: int, op_name: str, timeout: float = 180.0,
) -> list[Any]:
    """Run ``work(item, heartbeat)`` over ``items`` in a bounded pool under a watchdog."""
    todo = list(items)
    if not todo:
        return []
    dog = OperationWatchdog(op_name, timeout=timeout)
    dog.start()

    def task(indexed: tuple[int, Any]) -> Any:
        idx, item = indexed
        with monitored_worker(dog, f"{op_name}-{idx}") as beat:
            return work(item, beat)

    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415 - lazy: only when parallel
    try:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            return list(pool.map(task, enumerate(todo)))
    finally:
        dog.stop()
