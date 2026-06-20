"""Option 2 engine adapter (dual-libVLC gapless switching + audio crossfade).

Split out of :mod:`ytdl.infra.playback.engines` to keep each file ≤150 lines.
Builds a configured :class:`LibVlcPlayerMatrix` and drives it per track/segment.
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
from ytdl.services.mixer.segment import MixSegment


def _segment_mix_point(
    seg: MixSegment, duration_fn: Callable[..., float], ffmpeg: FfmpegLocator
) -> float:
    """Mix-out point of ``seg`` = ``start`` + play window (probed if ``None``)."""
    play = seg.play_seconds
    if play is None:
        play = duration_fn(seg.path, ffmpeg.exe())
    return seg.start + play


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

    def play_segments(self, segments: list[MixSegment], *, crossfade: float) -> None:
        """Drive the matrix with each segment's in-point and mix point."""
        if not segments:
            return
        matrix = self._matrix_factory(
            vlc_module=self._vlc,
            clock=self._clock,
            sleep=self._sleep,
            crossfade=crossfade,
            source_mix_time=None,
            target_start_time=segments[0].start,
        )
        active, idle = matrix.player_a, matrix.player_b
        matrix.target_start_time = segments[0].start
        matrix._prepare_next(active, segments[0].path)
        for index in range(len(segments) - 1):
            source, target = segments[index], segments[index + 1]
            matrix.target_start_time = target.start
            matrix._prepare_next(idle, target.path)
            matrix.source_mix_time = _segment_mix_point(source, self._duration_fn, self._ffmpeg)
            active = matrix.crossfade_pair(active, idle, matrix.source_mix_time)
            idle = matrix.player_a if active is matrix.player_b else matrix.player_b
