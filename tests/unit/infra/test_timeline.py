"""Unit tests for the absolute-timeline overlay compositor."""

from __future__ import annotations

from unittest.mock import MagicMock

from ytdl.infra.playback.timeline import build_timeline_command, timeline_total
from ytdl.services.mixer.segment import MixSegment


def _renderer() -> MagicMock:
    r = MagicMock()
    r._canvas = (1280, 720)
    r._fps = 30
    r._ffmpeg.exe.return_value = "/fake/ffmpeg"
    # Mirror MixRenderer._codec_out: append the output path as the final arg.
    r._codec_out.side_effect = lambda path: ["-c:v", "libx264", "-c:a", "aac", path]
    return r


def test_timeline_total_is_max_end() -> None:
    segs = [
        MixSegment("a.ts", at=0.0, play_seconds=8.0),
        MixSegment("b.ts", at=10.0, play_seconds=8.0),
    ]
    assert timeline_total(segs) == 18.0


def test_build_timeline_overlays_each_clip_at_its_time_with_leading_audio() -> None:
    segs = [
        MixSegment("0.ts", at=0.0, play_seconds=8.0),
        MixSegment("1.ts", at=10.0, play_seconds=8.0),
    ]
    cmd = build_timeline_command(
        _renderer(), segs, total=18.0, leading_path="song.mp3",
        leading_kind="audio", crossfade=2.0, output_path="out.mp4",
    )
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "color=c=black:s=1280x720" in graph and "d=18" in graph  # base = total
    assert graph.count("overlay=") == 2  # one overlay per clip
    assert "between(t,0,8)" in graph and "between(t,10,18)" in graph
    assert "setpts=PTS+10/TB" in graph  # second clip shifted to its absolute time
    # leading audio: looped to cover, trimmed to total, faded out
    assert "-stream_loop" in cmd
    assert "atrim=0:18" in graph and "afade=t=out" in graph
    # clips are inputs 1.. (leading is input 0)
    assert "[1:v]setpts" in graph
    assert cmd[0] == "/fake/ffmpeg" and cmd[-1] == "out.mp4"


def test_build_timeline_without_leading_is_video_only() -> None:
    segs = [MixSegment("0.ts", at=0.0, play_seconds=5.0)]
    cmd = build_timeline_command(
        _renderer(), segs, total=5.0, leading_path=None,
        leading_kind="none", crossfade=2.0, output_path="out.mp4",
    )
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "-stream_loop" not in cmd  # no leading input
    assert "atrim" not in graph  # no audio chain
    assert "[0:v]setpts" in graph  # clip is input 0 when there is no leading audio
    assert cmd.count("-map") == 1  # video only
