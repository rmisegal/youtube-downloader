"""FETCH stage — download the scenes' videos via a watchdog-monitored bounded pool.

Downloads are independent I/O, so a bounded thread pool fetches several clips at once
(the gatekeeper serializes only the cheap rate/quota check; the slow network calls
overlap). Concurrency safety follows Dr. Segal's Safe-Race pattern (``shared.concurrency``):
a bounded pool + an OperationWatchdog (heartbeat hang detection) + a single Lock guarding
the shared result lists. Already-present files are skipped (resume); failures are recorded
and the rest continue. Each download fetches only the scene's in-point window (section).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ytdl.shared.concurrency import run_pool

DownloadFn = Callable[[str, str, dict[str, Any]], Any]  # (url, dest_basename, segment)
DEFAULT_WORKERS = 6


def fetch_segments(
    download_fn: DownloadFn, segments: list[dict[str, Any]], videos_dir: str,
    *, workers: int = DEFAULT_WORKERS,
) -> tuple[list[int], list[int]]:
    """Download every missing segment's video concurrently; return (done, failed)."""
    vids = Path(videos_dir)
    vids.mkdir(parents=True, exist_ok=True)
    ordered = sorted(segments, key=lambda s: s.get("sequence_number", 0))
    done: list[int] = [s["sequence_number"] for s in ordered
                       if (vids / f"seg_{s['sequence_number']}.mp4").exists()]
    todo = [s for s in ordered if s["sequence_number"] not in done]
    failed: list[int] = []
    total = len(ordered)
    lock = threading.Lock()  # the ONE mutex guarding done/failed (held only for the append)

    def work(seg: dict[str, Any], heartbeat: Callable[..., None]) -> None:
        n = seg["sequence_number"]
        heartbeat(f"download seg_{n}")
        try:
            download_fn(seg.get("video_url", ""), f"seg_{n}", seg)
            with lock:
                done.append(n)
                print(f"[fetch {len(done) + len(failed)}/{total}] seg_{n} ok", flush=True)
        except Exception as exc:  # noqa: BLE001 - record + continue with the rest
            with lock:
                failed.append(n)
                print(f"[fetch] seg_{n} FAILED: {exc}", flush=True)

    run_pool(todo, work, workers=workers, op_name="fetch", timeout=300.0)
    return sorted(done), sorted(failed)
