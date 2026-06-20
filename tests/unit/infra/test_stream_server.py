"""Unit tests for :class:`ytdl.infra.playback.stream_server.StreamServer`.

``FfmpegLocator.exe`` is mocked to a fake path and ``runner`` is injected — no
real subprocess, no network, no VLC.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from ytdl.infra.ffmpeg import FfmpegLocator
from ytdl.infra.playback.stream_server import StreamServer

FAKE_FFMPEG = "/fake/bin/ffmpeg.exe"
SOURCE = "/media/a.mp4"
TARGET = "/media/b.mp4"


def _server(runner: object | None = None) -> StreamServer:
    return StreamServer(ffmpeg=FfmpegLocator(), runner=runner or MagicMock())


def _cmd(server: StreamServer, **kwargs: object) -> list[str]:
    with patch.object(FfmpegLocator, "exe", return_value=FAKE_FFMPEG):
        return server.build_pair_command(SOURCE, TARGET, **kwargs)  # type: ignore[arg-type]


def test_default_mix_point_uses_duration_minus_crossfade() -> None:
    """source_mix_time=None → offset = source_duration - crossfade."""
    cmd = _cmd(_server(), crossfade=3, source_duration=100)
    joined = " ".join(cmd)
    assert "offset=97" in joined
    assert "duration=3" in joined


def test_explicit_source_mix_time_sets_offset() -> None:
    """An explicit source_mix_time overrides the computed offset."""
    cmd = _cmd(_server(), crossfade=3, source_duration=100, source_mix_time=30)
    assert "offset=30" in " ".join(cmd)


def test_target_start_time_seeks_before_target_input() -> None:
    """-ss <target_start_time> appears immediately before the target -i."""
    cmd = _cmd(_server(), crossfade=3, source_duration=100, target_start_time=10)
    ss_idx = cmd.index("-ss")
    assert cmd[ss_idx + 1] == "10"
    assert cmd[ss_idx + 2] == "-i"
    assert cmd[ss_idx + 3] == TARGET


def test_source_input_has_no_seek() -> None:
    """The source -i is not preceded by an -ss (source plays from its start)."""
    cmd = _cmd(_server(), crossfade=3, source_duration=100)
    source_idx = cmd.index(SOURCE)
    assert cmd[source_idx - 1] == "-i"
    # only one -ss in the whole command (the target's)
    assert cmd.count("-ss") == 1


def test_command_uses_locator_path_and_mpegts_pipe() -> None:
    """argv[0] is the locator path; output is mpegts to pipe:1."""
    cmd = _cmd(_server(), crossfade=3, source_duration=100)
    assert cmd[0] == FAKE_FFMPEG
    assert cmd[-3:] == ["-f", "mpegts", "pipe:1"]


def test_xfade_and_acrossfade_both_present() -> None:
    """Both the video xfade and the audio acrossfade filters are emitted."""
    cmd = _cmd(_server(), crossfade=3, source_duration=100)
    joined = " ".join(cmd)
    assert "xfade=transition=fade" in joined
    assert "acrossfade=d=3" in joined
    assert "-map" in cmd and "[v]" in cmd and "[a]" in cmd


def test_stream_pair_invokes_runner_for_ffmpeg_and_vlc() -> None:
    """stream_pair starts ffmpeg (PIPE) and a vlc '-' reading that pipe."""
    runner = MagicMock()
    ffmpeg_proc = MagicMock()
    runner.side_effect = [ffmpeg_proc, MagicMock()]
    server = _server(runner)
    with patch.object(FfmpegLocator, "exe", return_value=FAKE_FFMPEG):
        server.stream_pair(
            SOURCE,
            TARGET,
            crossfade=3,
            source_duration=100,
            vlc_binary="myvlc",
        )
    assert runner.call_count == 2
    # First call: ffmpeg argv with stdout=PIPE.
    ffmpeg_args, ffmpeg_kwargs = runner.call_args_list[0]
    assert ffmpeg_args[0][0] == FAKE_FFMPEG
    assert ffmpeg_kwargs["stdout"] == subprocess.PIPE
    # Second call: vlc reading the ffmpeg pipe on stdin.
    vlc_args, vlc_kwargs = runner.call_args_list[1]
    assert vlc_args[0] == ["myvlc", "-"]
    assert vlc_kwargs["stdin"] == ffmpeg_proc.stdout
