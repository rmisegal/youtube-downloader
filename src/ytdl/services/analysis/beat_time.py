"""Resolve an overlay element's timeline to seconds (beats preferred, seconds fallback).

A :class:`~ytdl.services.playlist.track_model.TrackElement` may time itself in
leading-track BEATS (``at_beat`` + ``for_beats``) — resolved against the analyzed
beat grid so it snaps to the music — or in absolute ``at``/``until`` SECONDS. The
result is clamped to ``[0, total]``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def _beat_time(index: int, beats: Sequence[float], total: float) -> float:
    """Seconds of beat ``index`` (extrapolate past the last beat at the mean period)."""
    if not beats:
        return 0.0
    if index < len(beats):
        return float(beats[max(0, index)])
    period = (beats[-1] - beats[0]) / max(1, len(beats) - 1) if len(beats) > 1 else 0.5
    return min(total, float(beats[-1]) + period * (index - len(beats) + 1))


def resolve_timing(element: Any, beats: Sequence[float], total: float) -> tuple[float, float]:
    """Return ``(at_sec, until_sec)`` for ``element`` (beats preferred)."""
    if element.at_beat is not None:
        at = _beat_time(element.at_beat, beats, total)
        span_beats = element.for_beats if element.for_beats is not None else 4
        until = _beat_time(element.at_beat + max(1, span_beats), beats, total)
    else:
        at = float(element.at if element.at is not None else 0.0)
        until = float(element.until if element.until is not None else total)
    at = max(0.0, min(at, total))
    until = max(at, min(until, total))
    return at, until
