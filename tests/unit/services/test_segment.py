"""Unit tests for :class:`MixSegment` value object (PRD-playlist §2)."""

from __future__ import annotations

import dataclasses

import pytest

from ytdl.constants import EFFECT_FADE
from ytdl.services.mixer.segment import MixSegment


def test_defaults() -> None:
    seg = MixSegment(path="clip.mp4")
    assert seg.path == "clip.mp4"
    assert seg.start == 0.0
    assert seg.play_seconds is None
    assert seg.speed == 1.0
    assert seg.resolution == "max"
    assert seg.subtitle is None
    assert seg.effect == EFFECT_FADE == "fade"


def test_explicit_values_stored() -> None:
    seg = MixSegment(
        path="C:/x/clip.mkv",
        start=12.0,
        play_seconds=10.0,
        speed=1.25,
        resolution="1280x720",
        subtitle="clip.he.srt",
        effect="fade",
    )
    assert seg.path == "C:/x/clip.mkv"
    assert seg.start == 12.0
    assert seg.play_seconds == 10.0
    assert seg.speed == 1.25
    assert seg.resolution == "1280x720"
    assert seg.subtitle == "clip.he.srt"
    assert seg.effect == "fade"


def test_is_frozen() -> None:
    seg = MixSegment(path="clip.mp4")
    with pytest.raises(dataclasses.FrozenInstanceError):
        seg.start = 5.0  # type: ignore[misc]
