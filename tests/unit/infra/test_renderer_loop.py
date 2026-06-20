"""Unit tests for crossfade-looped leading audio (renderer_loop + looped_leading)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ytdl.infra.playback.renderer import MixRenderer
from ytdl.infra.playback.renderer_loop import build_loop_command, loop_copies


@pytest.mark.parametrize(
    ("audio", "video", "cf", "expected"),
    [
        (200.0, 20.0, 2.0, 0),    # song longer than video -> no loop
        (20.0, 20.0, 2.0, 0),     # equal -> no loop
        (0.0, 20.0, 2.0, 0),      # degenerate
        (2.0, 20.0, 2.0, 0),      # audio <= crossfade -> hard-loop fallback
        (10.0, 25.0, 2.0, 3),     # ceil((25-2)/(10-2)) = ceil(2.875) = 3
        (12.0, 20.0, 2.0, 2),     # ceil((20-2)/(12-2)) = ceil(1.8) = 2
    ],
)
def test_loop_copies(audio, video, cf, expected) -> None:
    assert loop_copies(audio, video, cf) == expected


def test_build_loop_command_chains_acrossfade() -> None:
    cmd = build_loop_command("/fake/ffmpeg", "song.mp3", 3, 2, "loop.m4a")
    # 3 inputs of the same song, 2 acrossfade seams, final label [aout] -> aac file.
    assert cmd.count("-i") == 3
    assert all(cmd[i + 1] == "song.mp3" for i, t in enumerate(cmd) if t == "-i")
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert graph.count("acrossfade=d=2") == 2
    assert "[0][1]acrossfade" in graph
    assert "[aout]" in graph
    assert cmd[-3:] == ["-c:a", "aac", "loop.m4a"]


def _renderer(audio_seconds: float, runner: MagicMock) -> MixRenderer:
    ff = MagicMock()
    ff.exe.return_value = "/fake/ffmpeg"
    return MixRenderer(ffmpeg=ff, runner=runner, duration_fn=lambda *_a: audio_seconds)


def test_looped_leading_returns_original_when_song_long_enough(tmp_path) -> None:
    runner = MagicMock()
    r = _renderer(audio_seconds=200.0, runner=runner)
    out = r.looped_leading("song.mp3", video_seconds=20.0, crossfade=2.0, tmp_dir=str(tmp_path))
    assert out == "song.mp3"
    runner.assert_not_called()  # no loop render needed


def test_looped_leading_renders_loop_when_song_short(tmp_path) -> None:
    from pathlib import Path

    seen: dict[str, list[str]] = {}

    def fake_runner(cmd, **_kw):  # type: ignore[no-untyped-def]
        Path(cmd[-1]).write_text("loopfile")  # simulate ffmpeg writing the loop
        seen["cmd"] = cmd
        return MagicMock()

    r = _renderer(audio_seconds=10.0, runner=fake_runner)  # type: ignore[arg-type]
    out = r.looped_leading("song.mp3", video_seconds=25.0, crossfade=2.0, tmp_dir=str(tmp_path))
    assert out.endswith("leadloop.m4a")
    assert seen["cmd"].count("-i") == 3  # ceil((25-2)/(10-2)) = 3 copies
