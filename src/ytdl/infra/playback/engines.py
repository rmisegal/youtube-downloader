"""Engine adapters presenting the interface :class:`MixerService` calls.

`MixerService` invokes ``stream_server.run(...)`` (Option 1) and
``matrix.play_sequence(timing...)`` (Option 2) with per-call timing but no
durations. These thin adapters wrap the Phase-B engines (:class:`StreamServer`,
:class:`LibVlcPlayerMatrix`), probe each source's duration (so the default
mix-out point = ``duration − crossfade``), and configure the underlying engine.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from ytdl.infra.ffmpeg import FfmpegLocator
from ytdl.infra.playback.duration import probe_duration
from ytdl.infra.playback.libvlc_matrix import LibVlcPlayerMatrix
from ytdl.infra.playback.stream_server import StreamServer


class Option1Engine:
    """Option 1 adapter: stream consecutive crossfade pairs through VLC."""

    def __init__(
        self,
        stream_server: StreamServer | None = None,
        ffmpeg: FfmpegLocator | None = None,
        duration_fn: Callable[..., float] = probe_duration,
    ) -> None:
        self._ffmpeg = ffmpeg or FfmpegLocator()
        self._stream = stream_server or StreamServer(self._ffmpeg)
        self._duration_fn = duration_fn

    def run(
        self,
        tracks: Sequence[Path | str],
        *,
        crossfade: float,
        source_mix_time: float | None,
        target_start_time: float | None,
        vlc_binary: str | None = None,
    ) -> None:
        """Stream each consecutive (source → target) pair with a true crossfade."""
        for index in range(len(tracks) - 1):
            source = str(tracks[index])
            duration = self._duration_fn(source, self._ffmpeg.exe())
            self._stream.stream_pair(
                source,
                str(tracks[index + 1]),
                crossfade=crossfade,
                source_duration=duration,
                source_mix_time=source_mix_time,
                target_start_time=target_start_time or 0.0,
                vlc_binary=vlc_binary,
            )


class Option2Engine:
    """Option 2 adapter: build a configured dual-libVLC matrix and play the FIFO."""

    def __init__(
        self,
        vlc_module: ModuleType | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        ffmpeg: FfmpegLocator | None = None,
        duration_fn: Callable[..., float] = probe_duration,
        matrix_factory: Callable[..., Any] = LibVlcPlayerMatrix,
    ) -> None:
        self._vlc = vlc_module
        self._clock = clock
        self._sleep = sleep
        self._ffmpeg = ffmpeg or FfmpegLocator()
        self._duration_fn = duration_fn
        self._matrix_factory = matrix_factory

    def play_sequence(
        self,
        tracks: Sequence[Path | str],
        *,
        crossfade: float,
        source_mix_time: float | None,
        target_start_time: float | None,
    ) -> None:
        """Probe durations, build the configured matrix, and play the sequence."""
        paths = [str(t) for t in tracks]
        durations = [self._duration_fn(p, self._ffmpeg.exe()) for p in paths]
        matrix = self._matrix_factory(
            vlc_module=self._vlc,
            clock=self._clock,
            sleep=self._sleep,
            crossfade=crossfade,
            source_mix_time=source_mix_time,
            target_start_time=target_start_time or 0.0,
        )
        matrix.play_sequence(paths, durations)
