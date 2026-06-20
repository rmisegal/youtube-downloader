"""StreamServer (Option 1): FFmpeg xfade/acrossfade composite piped into VLC.

Builds an FFmpeg command that blends a *source* clip into a *target* clip with a
true per-frame video (``xfade``) + audio (``acrossfade``) crossfade, muxes the
result as ``mpegts`` to stdout, and feeds that pipe into a standalone ``vlc -``
process. Process spawning is injected (``runner``) so unit tests never spawn
real processes — they assert command construction and the runner calls.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any

from ytdl.infra.ffmpeg import FfmpegLocator

# Default binary name for a VLC reading from stdin (``vlc -``).
DEFAULT_VLC_BINARY = "vlc"


def _fmt(value: float) -> str:
    """Format a time/duration as a compact string (no trailing ``.0``)."""
    return str(int(value)) if float(value).is_integer() else str(value)


def build_filter_complex(crossfade: float, offset: float) -> str:
    """Return the ``filter_complex`` string for the video+audio crossfade."""
    video = (
        f"[0:v][1:v]xfade=transition=fade:"
        f"duration={_fmt(crossfade)}:offset={_fmt(offset)}[v]"
    )
    audio = f"[0:a][1:a]acrossfade=d={_fmt(crossfade)}[a]"
    return f"{video};{audio}"


class StreamServer:
    """Option 1 engine: FFmpeg crossfade composite → VLC stdin."""

    def __init__(
        self,
        ffmpeg: FfmpegLocator | None = None,
        runner: Callable[..., Any] = subprocess.Popen,
    ) -> None:
        self._ffmpeg = ffmpeg or FfmpegLocator()
        self._runner = runner

    def build_pair_command(
        self,
        source: str,
        target: str,
        *,
        crossfade: float,
        source_duration: float,
        source_mix_time: float | None = None,
        target_start_time: float = 0.0,
        vlc_binary: str | None = None,  # noqa: ARG002 - parity with stream_pair
    ) -> list[str]:
        """Build the ffmpeg argv blending ``source`` into ``target`` to mpegts."""
        if source_mix_time is not None:
            offset = source_mix_time
        else:
            offset = max(0.0, source_duration - crossfade)
        filter_complex = build_filter_complex(crossfade, offset)
        return [
            self._ffmpeg.exe(),
            "-y",
            "-i",
            source,
            "-ss",
            _fmt(target_start_time),
            "-i",
            target,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-f",
            "mpegts",
            "pipe:1",
        ]

    def stream_pair(
        self,
        source: str,
        target: str,
        *,
        crossfade: float,
        source_duration: float,
        source_mix_time: float | None = None,
        target_start_time: float = 0.0,
        vlc_binary: str | None = None,
    ) -> tuple[Any, Any]:
        """Start ffmpeg, pipe its mpegts stdout into ``vlc -``; return handles."""
        command = self.build_pair_command(
            source,
            target,
            crossfade=crossfade,
            source_duration=source_duration,
            source_mix_time=source_mix_time,
            target_start_time=target_start_time,
        )
        ffmpeg_proc = self._runner(command, stdout=subprocess.PIPE)
        vlc_cmd = [vlc_binary or DEFAULT_VLC_BINARY, "-"]
        vlc_proc = self._runner(vlc_cmd, stdin=ffmpeg_proc.stdout)
        return ffmpeg_proc, vlc_proc
