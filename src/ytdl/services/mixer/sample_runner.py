"""``SampleRunner`` — orchestrate ``--sample-play`` over injected collaborators.

Builds mid-band :class:`MixSegment`s via the :class:`Sampler`, verifies the VLC
dependency for the chosen mode, then dispatches to the Option-1 stream server or
the Option-2 libVLC matrix — looping while ``sampler.loop`` (bounded by an
injectable ``should_continue`` so tests never spin forever). Pure orchestration;
no VLC/FFmpeg imports here (those live in the injected engines). ≤150 lines.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ytdl.constants import PLAYBACK_OPTION1

_DEFAULT_MODE = ("playback.default_mode", "option2")
_CROSSFADE = ("playback.crossfade_duration_seconds", 3)


class SampleRunner:
    """Preview a folder by crossfading random mid-band samples (PRD-playlist §3)."""

    def __init__(
        self,
        config: Any,
        sampler: Any,
        vlc_locator: Any,
        option1: Any,
        option2: Any,
        should_continue: Callable[[int], bool] | None = None,
    ) -> None:
        """Store config + injected collaborators (see module docstring)."""
        self._config = config
        self._sampler = sampler
        self._vlc = vlc_locator
        self._option1 = option1
        self._option2 = option2
        self._should_continue = should_continue or (lambda iteration: iteration < 1)

    def run(
        self,
        directory: Path | str,
        *,
        play_for_sec: float | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        """Build segments, check VLC, and play them (looped per ``sampler.loop``)."""
        segments = self._sampler.build_segments(directory, play_for_sec=play_for_sec)
        mode = mode if mode is not None else self._config.get(*_DEFAULT_MODE)
        crossfade = self._config.get(*_CROSSFADE)
        iteration = 0
        while True:
            self._play_once(mode, segments, crossfade)
            iteration += 1
            if not self._sampler.loop or not self._should_continue(iteration):
                break
        return {"mode": mode, "track_count": len(segments), "loop": self._sampler.loop}

    def _play_once(self, mode: str, segments: list[Any], crossfade: float) -> None:
        """Verify the VLC dep for ``mode`` and play the segments once."""
        if mode == PLAYBACK_OPTION1:
            vlc = self._vlc.vlc_binary()
            self._option1.run_segments(segments, crossfade=crossfade, vlc_binary=vlc)
        else:
            self._vlc.ensure_libvlc()
            self._option2.play_segments(segments, crossfade=crossfade)
