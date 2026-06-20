"""Unit tests for ``SampleRunner`` (sample-play dispatch / loop) — no VLC/FFmpeg.

The sampler + engines are MagicMocks; the VLC dependency check is asserted and a
missing-VLC error is shown to propagate (PRD-playlist §3).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ytdl.services.mixer.sample_runner import SampleRunner
from ytdl.services.mixer.segment import MixSegment
from ytdl.shared.config import ConfigManager
from ytdl.shared.errors import PlaybackDependencyError


def _config(mode: str = "option2") -> ConfigManager:
    return ConfigManager(
        data={
            "version": "1.02",
            "playback": {"default_mode": mode, "crossfade_duration_seconds": 2},
        }
    )


def _runner(*, mode: str = "option2", loop: bool = False, should_continue=None):  # type: ignore[no-untyped-def]
    sampler = MagicMock()
    sampler.loop = loop
    sampler.build_segments.return_value = [MixSegment(path="a.mp4", play_seconds=10)]
    vlc, opt1, opt2 = MagicMock(), MagicMock(), MagicMock()
    run = SampleRunner(
        _config(mode),
        sampler=sampler,
        vlc_locator=vlc,
        option1=opt1,
        option2=opt2,
        should_continue=should_continue,
    )
    return run, {"sampler": sampler, "vlc": vlc, "opt1": opt1, "opt2": opt2}


def test_sample_play_dispatches_option2_by_default() -> None:
    run, m = _runner(mode="option2")
    out = run.run("C:/videos", play_for_sec=8.0)
    m["sampler"].build_segments.assert_called_once_with("C:/videos", play_for_sec=8.0)
    m["vlc"].ensure_libvlc.assert_called_once()
    m["opt2"].play_segments.assert_called_once()
    m["opt1"].run_segments.assert_not_called()
    assert out == {"mode": "option2", "track_count": 1, "loop": False}


def test_sample_play_option1_when_mode_overrides() -> None:
    run, m = _runner(mode="option2")
    run.run("C:/videos", mode="option1")
    m["vlc"].vlc_binary.assert_called_once()
    m["opt1"].run_segments.assert_called_once()
    m["opt2"].play_segments.assert_not_called()


def test_sample_play_loops_bounded() -> None:
    run, m = _runner(loop=True, should_continue=lambda i: i < 2)
    run.run("C:/videos")
    assert m["opt2"].play_segments.call_count == 2


def test_missing_vlc_propagates() -> None:
    run, m = _runner(mode="option2")
    m["vlc"].ensure_libvlc.side_effect = PlaybackDependencyError("no vlc")
    with pytest.raises(PlaybackDependencyError):
        run.run("C:/videos")
