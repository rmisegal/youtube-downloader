"""Unit tests for the overlay-element beat/second timing resolver."""

from __future__ import annotations

from ytdl.services.analysis.beat_time import resolve_timing
from ytdl.services.playlist.track_model import TrackElement


def test_beats_preferred() -> None:
    beats = [float(i) for i in range(10)]
    assert resolve_timing(TrackElement(at_beat=2, for_beats=4), beats, 10.0) == (2.0, 6.0)


def test_default_span_is_four_beats() -> None:
    beats = [float(i) for i in range(12)]
    assert resolve_timing(TrackElement(at_beat=0), beats, 20.0) == (0.0, 4.0)


def test_seconds_fallback() -> None:
    assert resolve_timing(TrackElement(at=1.5, until=4.0), [], 10.0) == (1.5, 4.0)


def test_clamped_to_total() -> None:
    assert resolve_timing(TrackElement(at=5, until=999), [], 10.0) == (5.0, 10.0)


def test_extrapolates_past_last_beat() -> None:
    beats = [0.0, 1.0, 2.0]  # mean period 1.0
    at, until = resolve_timing(TrackElement(at_beat=4, for_beats=2), beats, 20.0)
    assert at == 4.0 and until == 6.0
