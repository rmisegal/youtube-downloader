"""Unit tests for the overlay-tracks command builder."""

from __future__ import annotations

from unittest.mock import MagicMock

from ytdl.infra.playback.overlay_tracks import build_overlay_command
from ytdl.services.playlist.track_model import TrackElement


def _renderer() -> MagicMock:
    r = MagicMock()
    r._ffmpeg.exe.return_value = "/ff"
    r._canvas = (1280, 720)
    r._codec_out.side_effect = lambda p: ["-c:v", "libx264", "-c:a", "aac", p]
    return r


def test_builds_one_drawtext_per_element_over_base() -> None:
    payload = {
        "elements": [TrackElement(text="A", at=0, until=4),
                     TrackElement(text="B", at=2, until=6, direction="left")],
        "beats": [], "total": 8.0, "bpm": 120.0,
    }
    cmd = build_overlay_command(_renderer(), "base.mp4", payload, "out.mp4")
    joined = " ".join(cmd)
    assert "base.mp4" in cmd and cmd[-1] == "out.mp4"  # base in, final out
    assert joined.count("drawtext=") == 2


def test_none_when_nothing_drawable() -> None:
    payload = {"elements": [TrackElement(text="", at=0, until=4),
                            TrackElement(text="X", at=5, until=5)],  # empty text / zero span
               "beats": [], "total": 8.0, "bpm": 120.0}
    assert build_overlay_command(_renderer(), "base.mp4", payload, "out.mp4") is None
