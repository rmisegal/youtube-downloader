"""``PlaylistRunner`` — orchestrate a YAML playlist into display/save/stream.

Pure orchestration over injected collaborators (Rule 1/2): loads + builds
segments, then routes per ``metadata.output`` (PRD-playlist §5.3 step 5):

* ``save``    → :class:`MixRenderer` renders ONE file (even when ``loop``).
* ``display`` → live VLC via Option-1/Option-2 engines (looped per ``loop``).
* ``stream``  → Option-1 local VLC loopback (``vlc -``).

No VLC/FFmpeg imports here; ``should_continue`` keeps the display loop bounded
in tests. Kept ≤150 code lines (heavy machinery lives in the collaborators).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

from ytdl.constants import (
    LEADING_AUDIO,
    LEADING_VIDEO,
    MIX_SUBTITLE,
    OUTPUT_DISPLAY,
    OUTPUT_SAVE,
    OUTPUT_STREAM,
    PLAYBACK_OPTION1,
)
from ytdl.services.mixer.segment import MixSegment
from ytdl.services.playlist.loader import load_playlist
from ytdl.services.playlist.loader_build import build_segments
from ytdl.services.playlist.summary import compute_summary

_DEFAULT_MODE = ("playback.default_mode", "option2")
_CROSSFADE = ("playback.crossfade_duration_seconds", 3)


class PlaylistRunner:
    """Run a YAML playlist across the enabled output routes (one report dict)."""

    def __init__(
        self,
        config: Any,
        vlc_locator: Any,
        option1: Any,
        option2: Any,
        renderer: Any,
        downloader: Any = None,
        crossfade: float | None = None,
        should_continue: Callable[[int], bool] | None = None,
    ) -> None:
        """Store config + injected collaborators (see module docstring)."""
        self._config = config
        self._vlc = vlc_locator
        self._option1 = option1
        self._option2 = option2
        self._renderer = renderer
        self._downloader = downloader
        self._crossfade = (
            crossfade if crossfade is not None else config.get(*_CROSSFADE)
        )
        # Bounded by default (one pass) so display tests never spin forever.
        self._should_continue = should_continue or (lambda iteration: iteration < 1)

    def run(self, yaml_path: str) -> dict[str, Any]:
        """Load, build, and route the playlist; return a small report dict."""
        playlist = load_playlist(yaml_path, downloader=self._downloader)
        segments = build_segments(playlist, downloader=self._downloader)
        meta = playlist.metadata
        # Honest mix gate: subtitle off => drop per-member subtitle requests.
        if not gate_subtitle(meta.active_mix_streams()):
            segments = [_drop_subtitle(seg) for seg in segments]
        outputs = meta.active_outputs()
        result: dict[str, Any] = {
            "outputs": outputs,
            "track_count": len(segments),
            "summary": compute_summary(segments, crossfade=self._crossfade),
        }
        if OUTPUT_SAVE in outputs:
            result["saved_path"] = self._save(playlist, segments)
        if OUTPUT_DISPLAY in outputs:
            self._display(meta, segments)
        if OUTPUT_STREAM in outputs:
            self._stream(segments)
        return result

    def _save(self, playlist: Any, segments: list[Any]) -> str:
        """Render the mix to ONE file under ``target_folder`` (once, no VLC)."""
        meta = playlist.metadata
        kind = meta.leading_kind()
        if kind in (LEADING_VIDEO, LEADING_AUDIO):
            return self._renderer.render(
                segments,
                meta.target_folder,
                crossfade=self._crossfade,
                leading_path=meta.leading_file(),
                leading_kind=kind,
            )
        return self._renderer.render(
            segments, meta.target_folder, crossfade=self._crossfade
        )

    def _display(self, meta: Any, segments: list[Any]) -> None:
        """Play the mix live, looping while ``loop`` (bounded by ``should_continue``)."""
        mode = self._config.get(*_DEFAULT_MODE)
        iteration = 0
        while True:
            self._play_once(mode, segments)
            iteration += 1
            if not meta.loop or not self._should_continue(iteration):
                break

    def _play_once(self, mode: str, segments: list[Any]) -> None:
        """Verify the VLC dep for ``mode`` and play the segments once."""
        if mode == PLAYBACK_OPTION1:
            vlc = self._vlc.vlc_binary()
            self._option1.run_segments(
                segments, crossfade=self._crossfade, vlc_binary=vlc
            )
        else:
            self._vlc.ensure_libvlc()
            self._option2.play_segments(segments, crossfade=self._crossfade)

    def _stream(self, segments: list[Any]) -> None:
        """Stream the mix over a local VLC loopback (Option-1 ``vlc -``)."""
        vlc = self._vlc.vlc_binary()
        self._option1.run_segments(
            segments, crossfade=self._crossfade, vlc_binary=vlc
        )


def gate_subtitle(active_mix_streams: list[str]) -> bool:
    """Whether the subtitle stream is requested (mix toggle honest gate)."""
    return MIX_SUBTITLE in active_mix_streams


def _drop_subtitle(segment: MixSegment) -> MixSegment:
    """Return ``segment`` with its subtitle request cleared (mix toggle off)."""
    return dataclasses.replace(segment, subtitle=None)
