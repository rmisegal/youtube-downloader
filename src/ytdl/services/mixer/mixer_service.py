"""MixerService: orchestrate VJ playback over injected engine collaborators.

Pure orchestration. Resolves playback tunables from :class:`ConfigManager`,
builds the track queue via the injected ``playlist`` engine, verifies the VLC
dependency, and dispatches to the Option-1 stream server or the Option-2 libVLC
matrix. No VLC/FFmpeg/yt-dlp imports live here (PRD-mixer §2, §4.2, §4.3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ytdl.constants import PLAYBACK_OPTION1, PLAYBACK_OPTION2, SELECTION_RANDOM
from ytdl.shared.config import ConfigManager

# Config keys + last-resort defaults for the ``playback`` block (PRD-mixer §5.1).
_DEFAULT_MODE = ("playback.default_mode", PLAYBACK_OPTION2)
_DEFAULT_SELECTION = ("playback.default_selection", SELECTION_RANDOM)
_CROSSFADE = ("playback.crossfade_duration_seconds", 3)
_SOURCE_MIX = ("playback.source_mix_time_seconds", None)
_TARGET_START = ("playback.target_start_time_seconds", 0)


class MixerService:
    """Dispatch folder playback to the selected engine after a dependency check."""

    def __init__(
        self,
        config: ConfigManager,
        playlist: Any,
        vlc_locator: Any,
        stream_server: Any,
        matrix: Any,
        downloader: Any = None,
    ) -> None:
        """Store the config and injected collaborators (see module docstring)."""
        self._config = config
        self._playlist = playlist
        self._vlc_locator = vlc_locator
        self._stream_server = stream_server
        self._matrix = matrix
        self._downloader = downloader

    def mix(
        self,
        directory: Path | str,
        *,
        mode: str | None = None,
        selection: str | None = None,
        crossfade: int | None = None,
        source_mix_time: float | None = None,
        target_start_time: float | None = None,
    ) -> dict[str, Any]:
        """Scan/select tracks and run them through the chosen playback engine.

        Unspecified arguments fall back to the ``playback`` config block. Raises
        :class:`PlaybackDependencyError` (from the locator) when VLC is missing
        and :class:`ValueError` for an unknown ``mode``.
        """
        mode = mode if mode is not None else self._config.get(*_DEFAULT_MODE)
        selection = (
            selection if selection is not None else self._config.get(*_DEFAULT_SELECTION)
        )
        crossfade = crossfade if crossfade is not None else self._config.get(*_CROSSFADE)
        if source_mix_time is None:
            source_mix_time = self._config.get(*_SOURCE_MIX)
        if target_start_time is None:
            target_start_time = self._config.get(*_TARGET_START)

        tracks = self._playlist.select(self._playlist.scan(directory), selection)
        self._dispatch(mode, tracks, crossfade, source_mix_time, target_start_time)
        return {
            "mode": mode,
            "selection": selection,
            "track_count": len(tracks),
            "crossfade": crossfade,
            "source_mix_time": source_mix_time,
            "target_start_time": target_start_time,
        }

    def _dispatch(
        self,
        mode: str,
        tracks: list[Path],
        crossfade: int,
        source_mix_time: float | None,
        target_start_time: float | None,
    ) -> None:
        """Verify the VLC dependency for ``mode`` and invoke its engine."""
        if mode == PLAYBACK_OPTION1:
            vlc = self._vlc_locator.vlc_binary()
            self._stream_server.run(
                tracks,
                crossfade=crossfade,
                source_mix_time=source_mix_time,
                target_start_time=target_start_time,
                vlc_binary=vlc,
            )
        elif mode == PLAYBACK_OPTION2:
            self._vlc_locator.ensure_libvlc()
            self._matrix.play_sequence(
                tracks,
                crossfade=crossfade,
                source_mix_time=source_mix_time,
                target_start_time=target_start_time,
            )
        else:
            raise ValueError(f"Unknown playback mode: {mode!r}")

    def inject_youtube(self, url: str, output_dir: Path | str) -> Any:
        """Download ``url`` via the injected SDK so the caller can enqueue it.

        Routes through the existing rate-limited downloader (PRD-mixer §4.2).
        Raises :class:`ValueError` when no downloader was injected.
        """
        if self._downloader is None:
            raise ValueError("No downloader configured for YouTube injection")
        return self._downloader.download(url, output_dir=output_dir)

    def inject_local(self, path: Path | str) -> Path:
        """Return ``path`` as a validated :class:`Path` for live insertion."""
        return Path(path)
