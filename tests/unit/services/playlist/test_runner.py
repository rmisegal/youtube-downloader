"""Unit tests for ``PlaylistRunner`` (output routing / loop / save-once / leading).

All collaborators are MagicMocks; ``load_playlist`` / ``build_segments`` are
patched in the runner module so no YAML/FFmpeg/VLC is touched (PRD-playlist §5.3).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ytdl.services.mixer.segment import MixSegment
from ytdl.services.playlist import runner as runner_module
from ytdl.services.playlist.model import (
    Leading,
    Metadata,
    MixToggles,
    Output,
    Playlist,
)
from ytdl.services.playlist.runner import PlaylistRunner
from ytdl.shared.config import ConfigManager


def _config(mode: str = "option2") -> ConfigManager:
    return ConfigManager(
        data={
            "version": "1.02",
            "playback": {"default_mode": mode, "crossfade_duration_seconds": 2},
        }
    )


def _playlist(*, output: Output, loop: bool = True, leading: Leading | None = None,
              mix: MixToggles | None = None) -> Playlist:
    meta = Metadata(
        target_folder="C:/out",
        output=output,
        mix=mix or MixToggles(),
        leading=leading or Leading(),
        loop=loop,
    )
    return Playlist(version="1.03", metadata=meta, members=[])


def _segments() -> list[MixSegment]:
    return [
        MixSegment(path="a.mp4", play_seconds=5, subtitle="a.srt"),
        MixSegment(path="b.mp4", play_seconds=5, subtitle=True),
    ]


def _runner(playlist: Playlist, *, mode: str = "option2", segments=None,
            should_continue=None):  # type: ignore[no-untyped-def]
    vlc, opt1, opt2, rend = (MagicMock() for _ in range(4))
    rend.render.return_value = "C:/out/mix.mp4"
    run = PlaylistRunner(
        _config(mode),
        vlc_locator=vlc,
        option1=opt1,
        option2=opt2,
        renderer=rend,
        should_continue=should_continue,
    )
    segs = segments if segments is not None else _segments()
    summary = {
        "total_length_seconds": 8.0,
        "total_file_size_bytes": 0,
        "resolution": "max",
        "members": [s.path for s in segs],
    }
    with patch.object(runner_module, "load_playlist", return_value=playlist), \
         patch.object(runner_module, "build_segments", return_value=segs), \
         patch.object(runner_module, "compute_summary", return_value=summary):
        result = run.run("show.yaml")
    return run, result, {"vlc": vlc, "opt1": opt1, "opt2": opt2, "rend": rend}


def test_save_renders_once_even_when_loop() -> None:
    pl = _playlist(output=Output(display=False, save=True), loop=True)
    _run, result, m = _runner(pl)
    m["rend"].render.assert_called_once()
    assert result["saved_path"] == "C:/out/mix.mp4"
    # Save must not display.
    m["opt2"].play_segments.assert_not_called()


def test_display_plays_via_option2_and_checks_vlc() -> None:
    pl = _playlist(output=Output(display=True), loop=False)
    _run, _result, m = _runner(pl, mode="option2")
    m["vlc"].ensure_libvlc.assert_called_once()
    m["opt2"].play_segments.assert_called_once()
    m["opt1"].run_segments.assert_not_called()


def test_display_option1_uses_vlc_binary() -> None:
    pl = _playlist(output=Output(display=True), loop=False)
    _run, _result, m = _runner(pl, mode="option1")
    m["vlc"].vlc_binary.assert_called()
    m["opt1"].run_segments.assert_called_once()


def test_display_timeline_routes_to_option1_with_timeline_flag() -> None:
    # An image (or any member with an absolute `at`) => timeline render via option1,
    # one VLC, NOT the per-clip option2 matrix.
    pl = _playlist(output=Output(display=True), loop=False)
    segs = [
        MixSegment(path="cover.jpg", kind="image", at=0.0, play_seconds=8.0),
        MixSegment(path="clip.mp4", at=8.0, play_seconds=10.0),
    ]
    _run, result, m = _runner(pl, mode="option2", segments=segs)
    assert result["timeline"] is True
    m["opt2"].play_segments.assert_not_called()
    m["opt1"].run_segments.assert_called_once()
    assert m["opt1"].run_segments.call_args.kwargs["timeline"] is True


def test_save_skipped_for_timeline_playlist() -> None:
    pl = _playlist(output=Output(display=False, save=True), loop=False)
    segs = [MixSegment(path="cover.jpg", kind="image", at=0.0, play_seconds=5.0)]
    _run, result, m = _runner(pl, segments=segs)
    m["rend"].render.assert_not_called()  # save skipped for timeline (logged)
    assert "saved_path" not in result


def test_display_leading_audio_renders_one_file_via_option1() -> None:
    # Leading track + default mode option2: must STILL render ONE file via
    # option1.run_segments (the matrix can't apply a separate leading soundtrack).
    pl = _playlist(
        output=Output(display=True),
        loop=False,
        leading=Leading(kind="audio", file="C:/song.mp4"),
        mix=MixToggles(video=True, audio=False),
    )
    _run, _result, m = _runner(pl, mode="option2")
    m["opt2"].play_segments.assert_not_called()
    m["opt1"].run_segments.assert_called_once()
    kw = m["opt1"].run_segments.call_args.kwargs
    assert kw["leading_kind"] == "audio"
    assert kw["leading_path"] == "C:/song.mp4"
    assert kw["vlc_binary"] is m["vlc"].vlc_binary.return_value


def test_display_loops_while_loop_true_bounded() -> None:
    pl = _playlist(output=Output(display=True), loop=True)
    _run, _result, m = _runner(pl, should_continue=lambda i: i < 3)
    assert m["opt2"].play_segments.call_count == 3


def test_stream_uses_option1_with_vlc_binary() -> None:
    pl = _playlist(output=Output(display=False, stream=True), loop=False)
    _run, _result, m = _runner(pl)
    m["opt1"].run_segments.assert_called_once()
    assert m["opt1"].run_segments.call_args.kwargs["vlc_binary"] is m["vlc"].vlc_binary.return_value


def test_leading_video_uses_leading_render_path() -> None:
    pl = _playlist(
        output=Output(display=False, save=True),
        leading=Leading(kind="video", file="lead.mp4"),
    )
    _run, _result, m = _runner(pl)
    kwargs = m["rend"].render.call_args.kwargs
    assert kwargs["leading_kind"] == "video"
    assert kwargs["leading_path"] == "lead.mp4"


def test_leading_audio_uses_leading_render_path() -> None:
    pl = _playlist(
        output=Output(display=False, save=True),
        leading=Leading(kind="audio", file="lead.mp3"),
    )
    _run, _result, m = _runner(pl)
    assert m["rend"].render.call_args.kwargs["leading_kind"] == "audio"


def test_summary_included_in_result() -> None:
    pl = _playlist(output=Output(display=True), loop=False)
    _run, result, _m = _runner(pl)
    assert set(result["summary"]) == {
        "total_length_seconds",
        "total_file_size_bytes",
        "resolution",
        "members",
    }
    assert result["track_count"] == 2
    assert result["outputs"] == ["display"]


def test_subtitle_toggle_off_drops_subtitle_in_render() -> None:
    pl = _playlist(
        output=Output(display=False, save=True),
        mix=MixToggles(subtitle=False),
    )
    _run, _result, m = _runner(pl)
    rendered_segments = m["rend"].render.call_args.args[0]
    assert all(seg.subtitle is None for seg in rendered_segments)


def test_subtitle_toggle_on_keeps_subtitle() -> None:
    pl = _playlist(
        output=Output(display=False, save=True),
        mix=MixToggles(subtitle=True),
    )
    _run, _result, m = _runner(pl)
    rendered_segments = m["rend"].render.call_args.args[0]
    assert any(seg.subtitle is not None for seg in rendered_segments)
