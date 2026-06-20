"""Unit tests for the additive segment-aware engine entry points (all mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock

from ytdl.infra.playback.engines import Option1Engine, Option2Engine
from ytdl.services.mixer.segment import MixSegment


def _ffmpeg() -> MagicMock:
    loc = MagicMock()
    loc.exe.return_value = "/fake/ffmpeg"
    return loc


def test_run_segments_streams_each_pair_with_segment_timing() -> None:
    stream = MagicMock()
    engine = Option1Engine(
        stream_server=stream, ffmpeg=_ffmpeg(), duration_fn=lambda *_a: 999.0
    )
    segs = [
        MixSegment("a.mp4", start=5.0, play_seconds=10.0),
        MixSegment("b.mp4", start=2.0, play_seconds=8.0),
        MixSegment("c.mp4", start=1.0, play_seconds=4.0),
    ]
    engine.run_segments(segs, crossfade=3, vlc_binary="/usr/bin/vlc")

    assert stream.stream_pair.call_count == 2  # (a->b), (b->c)
    first = stream.stream_pair.call_args_list[0]
    assert first.args == ("a.mp4", "b.mp4")
    assert first.kwargs["source_mix_time"] == 15.0  # start 5 + play 10
    assert first.kwargs["target_start_time"] == 2.0  # next seg's start
    assert first.kwargs["crossfade"] == 3
    assert first.kwargs["vlc_binary"] == "/usr/bin/vlc"


def test_run_segments_none_play_seconds_uses_probed_duration() -> None:
    stream = MagicMock()
    engine = Option1Engine(
        stream_server=stream, ffmpeg=_ffmpeg(), duration_fn=lambda *_a: 40.0
    )
    segs = [
        MixSegment("a.mp4", start=6.0, play_seconds=None),
        MixSegment("b.mp4", start=0.0, play_seconds=5.0),
    ]
    engine.run_segments(segs, crossfade=2)

    kw = stream.stream_pair.call_args.kwargs
    assert kw["source_mix_time"] == 46.0  # start 6 + probed 40
    assert kw["target_start_time"] == 0.0


def test_run_segments_single_segment_does_not_stream() -> None:
    stream = MagicMock()
    Option1Engine(stream_server=stream, ffmpeg=_ffmpeg()).run_segments(
        [MixSegment("only.mp4", start=1.0, play_seconds=3.0)], crossfade=3
    )
    stream.stream_pair.assert_not_called()


def _matrix_with_distinct_players() -> MagicMock:
    matrix = MagicMock()
    matrix.player_a = MagicMock(name="player_a")
    matrix.player_b = MagicMock(name="player_b")
    # crossfade_pair returns the deck handed to it (the idle/next deck).
    matrix.crossfade_pair.side_effect = lambda _active, nxt, _dur: nxt
    return matrix


def test_play_segments_drives_matrix_with_inpoints_and_mix_points() -> None:
    matrix = _matrix_with_distinct_players()
    factory = MagicMock(return_value=matrix)
    engine = Option2Engine(
        vlc_module="VLC",
        ffmpeg=_ffmpeg(),
        duration_fn=lambda *_a: 999.0,
        matrix_factory=factory,
    )
    segs = [
        MixSegment("a.mp4", start=5.0, play_seconds=10.0),
        MixSegment("b.mp4", start=2.0, play_seconds=8.0),
    ]
    engine.play_segments(segs, crossfade=4)

    # First clip is pre-seeked to its in-point (start=5.0).
    prep_paths = [c.args[1] for c in matrix._prepare_next.call_args_list]
    assert prep_paths == ["a.mp4", "b.mp4"]

    # The handoff mix point is source start + play_seconds = 15.0.
    cf = matrix.crossfade_pair.call_args_list[0]
    assert cf.args[2] == 15.0  # mix point drives crossfade_pair
    # The target deck was seeked to seg b's in-point before the handoff.
    factory.assert_called_once()
    assert factory.call_args.kwargs["target_start_time"] == 5.0  # first seg in-point


def test_play_segments_none_play_seconds_uses_probed_duration() -> None:
    matrix = _matrix_with_distinct_players()
    factory = MagicMock(return_value=matrix)
    engine = Option2Engine(
        vlc_module="VLC",
        ffmpeg=_ffmpeg(),
        duration_fn=lambda *_a: 30.0,
        matrix_factory=factory,
    )
    segs = [
        MixSegment("a.mp4", start=4.0, play_seconds=None),
        MixSegment("b.mp4", start=0.0, play_seconds=6.0),
    ]
    engine.play_segments(segs, crossfade=2)

    cf = matrix.crossfade_pair.call_args_list[0]
    assert cf.args[2] == 34.0  # start 4 + probed 30


def test_play_segments_empty_is_noop() -> None:
    factory = MagicMock()
    Option2Engine(matrix_factory=factory).play_segments([], crossfade=3)
    factory.assert_not_called()
