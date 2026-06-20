"""Unit tests for the additive segment-aware engine entry points (all mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock

from ytdl.infra.playback.engines import Option1Engine, Option2Engine
from ytdl.services.mixer.segment import MixSegment


def _ffmpeg() -> MagicMock:
    loc = MagicMock()
    loc.exe.return_value = "/fake/ffmpeg"
    return loc


def _sample_prep(prepare_returns) -> MagicMock:
    prep = MagicMock()
    prep.prepare.side_effect = prepare_returns
    return prep


def test_run_segments_preps_each_clip_then_renders_file_and_opens_vlc() -> None:
    import subprocess

    renderer = MagicMock()
    renderer.build_command.return_value = ["ffmpeg", "render", "mix.mp4"]
    runner = MagicMock()
    prep = _sample_prep([True, True, True])
    engine = Option1Engine(
        ffmpeg=_ffmpeg(), renderer=renderer, runner=runner, sample_prep=prep
    )
    segs = [
        MixSegment("a.mp4", start=5.0, play_seconds=10.0),
        MixSegment("b.mp4", start=2.0, play_seconds=8.0),
        MixSegment("c.mp4", start=1.0, play_seconds=4.0),
    ]
    engine.run_segments(segs, crossfade=3, vlc_binary="/usr/bin/vlc")

    # prepare() called ONCE PER SEGMENT (sequential prep — the heavy step).
    assert prep.prepare.call_count == 3
    # ONE renderer graph stitched into a real FILE (not a pipe) so VLC can replay.
    renderer.build_command.assert_called_once()
    args, kwargs = renderer.build_command.call_args
    prepared = args[0]
    assert len(prepared) == 3
    assert all(seg.start == 0.0 for seg in prepared)
    assert args[1].endswith("mix.mp4")  # render target is a file, not pipe:1
    assert kwargs["crossfade"] == 3
    assert "container" not in kwargs  # file output infers its muxer
    # render ffmpeg (stdin detached) THEN VLC opening the rendered FILE; both waited.
    assert runner.call_count == 2
    render_call, vlc_call = runner.call_args_list
    assert render_call.kwargs.get("stdin") is subprocess.DEVNULL
    assert vlc_call.args[0][0] == "/usr/bin/vlc"
    assert vlc_call.args[0][1].endswith("mix.mp4")
    assert runner.return_value.wait.call_count == 2


def test_run_segments_leading_audio_uses_leading_command() -> None:
    renderer = MagicMock()
    renderer.build_leading_command.return_value = ["ffmpeg", "lead", "mix.mp4"]
    runner = MagicMock()
    prep = _sample_prep([True, True])
    engine = Option1Engine(
        ffmpeg=_ffmpeg(), renderer=renderer, runner=runner, sample_prep=prep
    )
    segs = [MixSegment("a.mp4", play_seconds=5.0), MixSegment("b.mp4", play_seconds=5.0)]
    engine.run_segments(
        segs, crossfade=2, vlc_binary="/usr/bin/vlc",
        leading_path="song.mp4", leading_kind="audio",
    )
    # Leading => the leading renderer is used; the plain build_command is NOT.
    renderer.build_leading_command.assert_called_once()
    renderer.build_command.assert_not_called()
    args = renderer.build_leading_command.call_args.args  # (prepared, path, kind, out)
    assert args[1] == "song.mp4"
    assert args[2] == "audio"
    assert args[3].endswith("mix.mp4")


def test_run_segments_skips_failed_preps() -> None:
    renderer = MagicMock()
    renderer.build_command.return_value = ["ffmpeg"]
    runner = MagicMock()
    # Middle clip's prep fails -> it is SKIPPED, only 2 prepared clips remain.
    prep = _sample_prep([True, False, True])
    engine = Option1Engine(
        ffmpeg=_ffmpeg(), renderer=renderer, runner=runner, sample_prep=prep
    )
    segs = [
        MixSegment("a.mp4", play_seconds=10.0),
        MixSegment("bad.mp4", play_seconds=8.0),
        MixSegment("c.mp4", play_seconds=4.0),
    ]
    engine.run_segments(segs, crossfade=3)

    assert prep.prepare.call_count == 3
    prepared = renderer.build_command.call_args.args[0]
    assert len(prepared) == 2  # the failed clip was skipped


def test_run_segments_fewer_than_two_prepared_does_not_stream() -> None:
    renderer, runner = MagicMock(), MagicMock()
    prep = _sample_prep([True, False])
    engine = Option1Engine(
        ffmpeg=_ffmpeg(), renderer=renderer, runner=runner, sample_prep=prep
    )
    engine.run_segments(
        [MixSegment("a.mp4", play_seconds=3.0), MixSegment("b.mp4", play_seconds=3.0)],
        crossfade=3,
    )
    renderer.build_command.assert_not_called()
    runner.assert_not_called()


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
