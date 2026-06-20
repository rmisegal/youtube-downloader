"""LibVlcPlayerMatrix: Option 2 — dual-libVLC gapless switching + audio crossfade.

Two ``python-vlc`` media players (``Player_A`` / ``Player_B``) are double-buffered
so the idle deck silently pre-seeks the next track to its in-point while the active
deck plays. When the active deck reaches the mix-out point the decks hand off over
the ``crossfade`` window with an audio volume ramp (active 100→0, next 0→100).

Per PRD §4.3.2 this is *gapless switching with an audio crossfade* — libVLC does
not alpha-composite two video windows, so no per-pixel video blend is promised.

All timing flows through an injected ``clock``/``sleep`` so unit tests drive a fake
clock and never wait in real time; ``vlc`` is injectable (lazily imported only when
no module is supplied) so tests pass a mock module — no real rendering or timing.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from types import ModuleType
from typing import Any

_RAMP_STEPS = 10
_MAX_VOLUME = 100
_POLL_INTERVAL = 0.05


class LibVlcPlayerMatrix:
    """Drives two libVLC players for gapless handoff with an audio crossfade."""

    def __init__(
        self,
        *,
        vlc_module: ModuleType | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        crossfade: float,
        source_mix_time: float | None = None,
        target_start_time: float = 0.0,
    ) -> None:
        self._vlc = vlc_module if vlc_module is not None else self._import_vlc()
        self._clock = clock
        self._sleep = sleep
        self.crossfade = crossfade
        self.source_mix_time = source_mix_time
        self.target_start_time = target_start_time
        self.player_a = self._new_player()
        self.player_b = self._new_player()

    @staticmethod
    def _import_vlc() -> ModuleType:
        """Lazily import python-vlc (only when no module is injected)."""
        try:
            import vlc
        except ImportError as exc:  # pragma: no cover - covered by injection
            raise RuntimeError("python-vlc is required for Option 2") from exc
        return vlc

    def _new_player(self) -> Any:
        """Build a media player via ``Instance`` or the ``MediaPlayer`` shortcut."""
        instance_factory = getattr(self._vlc, "Instance", None)
        if instance_factory is not None:
            return instance_factory("--quiet").media_player_new()
        return self._vlc.MediaPlayer()

    def _prepare_next(self, player: Any, path: str) -> None:
        """Load ``path`` on ``player``, seek to the in-point, and silence it."""
        media = self._vlc.Media(path)
        player.set_media(media)
        player.set_time(int(self.target_start_time * 1000))
        player.audio_set_volume(0)

    def _mix_point(self, source_duration: float) -> float:
        """Resolve the mix-out position (explicit override or natural end)."""
        if self.source_mix_time is not None:
            return self.source_mix_time
        return max(0.0, source_duration - self.crossfade)

    def _wait_for_mix(self, active: Any, mix: float) -> None:
        """Poll ``active`` position (seconds) until it reaches ``mix``."""
        while active.get_time() / 1000 < mix:
            self._clock()
            self._sleep(_POLL_INTERVAL)

    def _ramp_audio(self, active: Any, nxt: Any) -> None:
        """Fade ``active`` 100→0 and ``nxt`` 0→100 across the crossfade window."""
        nxt.play()
        step = self.crossfade / _RAMP_STEPS
        for i in range(1, _RAMP_STEPS + 1):
            fraction = i / _RAMP_STEPS
            active.audio_set_volume(int(_MAX_VOLUME * (1 - fraction)))
            nxt.audio_set_volume(int(_MAX_VOLUME * fraction))
            self._clock()
            self._sleep(step)

    def crossfade_pair(self, active: Any, nxt: Any, source_duration: float) -> Any:
        """Play ``active``, hand off to ``nxt`` at the mix point, return ``nxt``.

        The active deck plays until its position reaches the mix-out point, then
        the audio is crossfaded over ``crossfade`` seconds while ``nxt`` starts;
        afterwards ``active`` stops and ``nxt`` becomes the new active deck.
        """
        active.audio_set_volume(_MAX_VOLUME)
        active.play()
        self._wait_for_mix(active, self._mix_point(source_duration))
        self._ramp_audio(active, nxt)
        active.stop()
        return nxt

    def play_sequence(
        self, tracks: Sequence[str], durations: Sequence[float]
    ) -> None:
        """Play a FIFO of ``tracks`` alternating A/B decks for gapless crossfades."""
        if not tracks:
            return
        active, idle = self.player_a, self.player_b
        self._prepare_next(active, tracks[0])
        for index in range(len(tracks) - 1):
            self._prepare_next(idle, tracks[index + 1])
            active = self.crossfade_pair(active, idle, durations[index])
            idle = self.player_a if active is self.player_b else self.player_b
