"""``Sampler`` — random mid-band segment builder for ``--sample-play`` (PRD-playlist §3).

Probes each clip's duration, seeks to a random point in the configured mid-band,
and emits ``list[MixSegment]`` (looping the folder is the caller's concern).

Implemented in Phase 5.1.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path

from ytdl.infra.ffmpeg import FfmpegLocator
from ytdl.infra.playback.duration import probe_duration
from ytdl.services.mixer.playlist_engine import PlaylistEngine
from ytdl.services.mixer.segment import MixSegment
from ytdl.shared.config import ConfigManager

# Config keys + defaults (Rule 11: no hardcoded tunables in logic).
_PLAY_SECONDS = ("sample.play_seconds", 10)
_MID_BAND_LOW = ("sample.mid_band_low", 0.25)
_MID_BAND_HIGH = ("sample.mid_band_high", 0.75)
_LOOP = ("sample.loop", True)


class Sampler:
    """Build random mid-band :class:`MixSegment`s for a folder of clips."""

    def __init__(
        self,
        config: ConfigManager,
        playlist_engine: PlaylistEngine | None = None,
        duration_fn: Callable[..., float] = probe_duration,
        rng: random.Random | None = None,
        ffmpeg: FfmpegLocator | None = None,
    ) -> None:
        """Store config plus injectable collaborators.

        Args:
            config: Source of the ``sample.*`` tunables.
            playlist_engine: Folder scanner (reuses the removable-drive guard +
                format filter). Defaults to a fresh :class:`PlaylistEngine`.
            duration_fn: Clip-duration prober (injected for tests).
            rng: Random source for the mid-band pick (inject a seeded
                :class:`random.Random` for deterministic tests).
            ffmpeg: FFmpeg locator passed to ``duration_fn``.
        """
        self._config = config
        self._engine = playlist_engine if playlist_engine is not None else PlaylistEngine(config)
        self._duration_fn = duration_fn
        self._rng = rng if rng is not None else random.Random()
        self._ffmpeg = ffmpeg if ffmpeg is not None else FfmpegLocator()

    @property
    def loop(self) -> bool:
        """Whether the folder should repeat (``sample.loop`` config)."""
        return bool(self._config.get(*_LOOP))

    def build_segments(
        self, directory: Path | str, *, play_for_sec: float | None = None
    ) -> list[MixSegment]:
        """Emit one mid-band :class:`MixSegment` per scanned track.

        Args:
            directory: Folder to scan (delegated to :class:`PlaylistEngine`).
            play_for_sec: Override for ``sample.play_seconds`` when not ``None``.

        Returns:
            One :class:`MixSegment` per track (a single, non-looping pass).
        """
        mid_low = float(self._config.get(*_MID_BAND_LOW))
        mid_high = float(self._config.get(*_MID_BAND_HIGH))
        play = play_for_sec if play_for_sec is not None else float(self._config.get(*_PLAY_SECONDS))
        exe = self._ffmpeg.exe()
        segments: list[MixSegment] = []
        for track in self._engine.scan(directory):
            duration = self._duration_fn(str(track), exe)
            start = self._rng.uniform(mid_low, mid_high) * duration
            segments.append(MixSegment(path=str(track), start=start, play_seconds=play))
        return segments
