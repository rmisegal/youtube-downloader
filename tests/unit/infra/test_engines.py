"""Unit tests for the Option-1/Option-2 engine adapters (all boundaries mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock

from ytdl.infra.playback.engines import Option1Engine, Option2Engine


def _ffmpeg() -> MagicMock:
    loc = MagicMock()
    loc.exe.return_value = "/fake/ffmpeg"
    return loc


def test_option1_streams_each_pair_with_probed_duration() -> None:
    stream = MagicMock()
    engine = Option1Engine(
        stream_server=stream, ffmpeg=_ffmpeg(), duration_fn=lambda *_a: 100.0
    )
    engine.run(
        ["a.mp4", "b.mp4", "c.mp4"],
        crossfade=3,
        source_mix_time=None,
        target_start_time=0.0,
        vlc_binary="/usr/bin/vlc",
    )
    assert stream.stream_pair.call_count == 2  # (a->b), (b->c)
    first = stream.stream_pair.call_args_list[0]
    assert first.args == ("a.mp4", "b.mp4")
    assert first.kwargs["source_duration"] == 100.0
    assert first.kwargs["crossfade"] == 3
    assert first.kwargs["vlc_binary"] == "/usr/bin/vlc"


def test_option1_explicit_mix_point_passed_through() -> None:
    stream = MagicMock()
    engine = Option1Engine(stream_server=stream, ffmpeg=_ffmpeg(), duration_fn=lambda *_a: 50.0)
    engine.run(["a.mp4", "b.mp4"], crossfade=2, source_mix_time=30.0, target_start_time=10.0)
    kw = stream.stream_pair.call_args.kwargs
    assert kw["source_mix_time"] == 30.0
    assert kw["target_start_time"] == 10.0


def test_option1_single_track_does_not_stream() -> None:
    stream = MagicMock()
    Option1Engine(stream_server=stream, ffmpeg=_ffmpeg()).run(
        ["only.mp4"], crossfade=3, source_mix_time=None, target_start_time=0.0
    )
    stream.stream_pair.assert_not_called()


def test_option2_builds_configured_matrix_and_plays() -> None:
    matrix = MagicMock()
    factory = MagicMock(return_value=matrix)
    engine = Option2Engine(
        vlc_module="VLC",
        ffmpeg=_ffmpeg(),
        duration_fn=lambda p, _e: 100.0,
        matrix_factory=factory,
    )
    engine.play_sequence(["a.mp4", "b.mp4"], crossfade=4, source_mix_time=30.0, target_start_time=5.0)
    fk = factory.call_args.kwargs
    assert fk["crossfade"] == 4
    assert fk["source_mix_time"] == 30.0
    assert fk["target_start_time"] == 5.0
    assert fk["vlc_module"] == "VLC"
    matrix.play_sequence.assert_called_once_with(["a.mp4", "b.mp4"], [100.0, 100.0])
