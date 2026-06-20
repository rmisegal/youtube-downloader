"""Playlist summary computor: total length / file size / resolution / members.

Computes the values written back into ``metadata.summary`` (PRD-playlist §5.3 step 7).

A pure ``compute_summary`` returns a dict with exactly the four ``metadata.summary``
keys; ``duration_fn`` and ``size_fn`` are injectable so unit tests need neither real
files nor FFmpeg. Implemented in Phase 5.5.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import Any

from ytdl.infra.playback.duration import probe_duration
from ytdl.services.mixer.segment import MixSegment

RESOLUTION_MAX = "max"


def _segment_height(resolution: str) -> int:
    """Return a comparable height for a ``"WxH"`` / ``"H"`` resolution (``"max"`` → 0)."""
    if not resolution or resolution == RESOLUTION_MAX:
        return 0
    tail = resolution.lower().split("x")[-1]
    try:
        return int(tail)
    except ValueError:
        return 0


def _resolution(segments: Sequence[MixSegment]) -> str:
    """Dominant member resolution: the tallest concrete ``WxH`` present, else ``"max"``.

    If no segment specifies a concrete resolution they are all ``"max"``.
    """
    concrete = [(_segment_height(s.resolution), s.resolution) for s in segments]
    concrete = [(h, r) for h, r in concrete if h > 0]
    if not concrete:
        return RESOLUTION_MAX
    return max(concrete, key=lambda pair: pair[0])[1]


def _play_window(
    segment: MixSegment,
    duration_fn: Callable[..., float],
    ffmpeg: Any,
) -> float:
    """Effective seconds played: ``play_seconds`` or the probed clip duration."""
    if segment.play_seconds is not None:
        return float(segment.play_seconds)
    exe = ffmpeg.exe() if ffmpeg is not None else ""
    return float(duration_fn(segment.path, exe))


def _total_length(
    segments: Sequence[MixSegment],
    crossfade: float,
    duration_fn: Callable[..., float],
    ffmpeg: Any,
) -> float:
    """Σ play windows − (N−1)·crossfade overlap, floored at 0.0."""
    total = sum(_play_window(s, duration_fn, ffmpeg) for s in segments)
    overlap = max(len(segments) - 1, 0) * crossfade
    return max(total - overlap, 0.0)


def _total_size(
    segments: Sequence[MixSegment],
    size_fn: Callable[[str], int],
) -> int:
    """Sum ``size_fn`` over each UNIQUE member file (each file counted once)."""
    seen: set[str] = set()
    total = 0
    for seg in segments:
        if seg.path in seen:
            continue
        seen.add(seg.path)
        total += int(size_fn(seg.path))
    return total


def compute_summary(
    segments: list[MixSegment],
    *,
    crossfade: float,
    duration_fn: Callable[..., float] = probe_duration,
    size_fn: Callable[[str], int] | None = None,
    ffmpeg: Any = None,
) -> dict:
    """Compute the four ``metadata.summary`` fields for a list of mix segments.

    Args:
        segments: Ordered mix segments.
        crossfade: Per-transition crossfade seconds (subtracted as overlap).
        duration_fn: ``(path, ffmpeg_exe) -> seconds`` for segments lacking
            ``play_seconds`` (injectable; defaults to ``probe_duration``).
        size_fn: ``(path) -> bytes`` (injectable; defaults to ``os.path.getsize``).
        ffmpeg: ``FfmpegLocator``-like object exposing ``.exe()`` (only used when a
            segment must be probed).

    Returns:
        ``{total_length_seconds, total_file_size_bytes, resolution, members}``.
    """
    size_of = size_fn if size_fn is not None else os.path.getsize
    return {
        "total_length_seconds": _total_length(segments, crossfade, duration_fn, ffmpeg),
        "total_file_size_bytes": _total_size(segments, size_of),
        "resolution": _resolution(segments),
        "members": [os.path.basename(s.path) for s in segments],
    }
