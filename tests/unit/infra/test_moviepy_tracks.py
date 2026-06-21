"""Unit tests for the MoviePy text-track routing + anchor logic (no real render)."""

from __future__ import annotations

from ytdl.infra.playback.moviepy_tracks import _anchor
from ytdl.infra.playback.sample_stream import _has_advanced_text
from ytdl.infra.playback.text_shape import font_path
from ytdl.services.playlist.track_model import TrackElement


def test_anchor_spreads_all_over_when_no_xy() -> None:
    ax, ay, size, color, _seed = _anchor(TrackElement(text="HELLO"), 1000, 800)
    assert 0 < ax < 1000 and 0 < ay < 800  # somewhere on screen, not forced centre
    assert size >= 44 and color


def test_anchor_uses_explicit_xy() -> None:
    ax, ay, _s, _c, _seed = _anchor(TrackElement(text="HI", x=0.5, y=0.25), 1000, 800)
    assert ax == 500.0 and ay == 200.0


def test_two_titles_get_different_default_anchors() -> None:
    a = _anchor(TrackElement(text="ALPHA"), 1000, 800)[:2]
    b = _anchor(TrackElement(text="OMEGA"), 1000, 800)[:2]
    assert a != b  # text-derived spread -> different positions


def test_font_resolves_to_a_ttf() -> None:
    assert font_path().lower().endswith(".ttf")


def test_advanced_effects_route_to_moviepy() -> None:
    assert _has_advanced_text({"elements": [TrackElement(text="A", effect="rotate")]}) is True
    assert _has_advanced_text({"elements": [TrackElement(text="A", effect="explode")]}) is True
    assert _has_advanced_text({"elements": [TrackElement(text="A", effect="move")]}) is False
    assert _has_advanced_text({"elements": []}) is False
