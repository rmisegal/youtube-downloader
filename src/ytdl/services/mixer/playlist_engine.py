"""PlaylistEngine: scan a folder for media and build a playback order.

Implements PRD-mixer §4.1 (folder scan + removable-drive safety) and §4.2
(random/manual selection). Pure queue building — no playback here.
"""

from __future__ import annotations

import random
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from ytdl.constants import SUPPORTED_VIDEO_FORMATS
from ytdl.shared.config import ConfigManager
from ytdl.shared.selection import expand_selection

# Removable/network drives that may be unmounted (global drive-safety rule).
_REMOVABLE_DRIVES = ("D:", "H:")


class PlaylistEngine:
    """Discover supported media in a directory and order it for playback."""

    def __init__(
        self,
        config: ConfigManager,
        shuffle_fn: Callable[[list[Path]], None] = random.shuffle,
        input_fn: Callable[[str], str] = input,
    ) -> None:
        """Store config and injectable shuffle/input collaborators.

        Args:
            config: Source of ``playback.supported_video_formats``.
            shuffle_fn: In-place list shuffler (injected for deterministic tests).
            input_fn: Reader for the manual picker prompt (injected for tests).
        """
        self._config = config
        self._shuffle = shuffle_fn
        self._input = input_fn

    @property
    def _formats(self) -> tuple[str, ...]:
        """Lower-cased supported extensions from config (fallback to constants)."""
        raw = self._config.get("playback.supported_video_formats", SUPPORTED_VIDEO_FORMATS)
        return tuple(str(ext).lower() for ext in raw)

    def scan(self, directory: Path | str) -> list[Path]:
        """Return a sorted list of supported media files in ``directory``.

        Raises:
            FileNotFoundError: if a removable drive is unmounted, or the
                directory does not exist / is not a directory.
        """
        path = Path(directory).resolve()
        self._guard_removable(path)
        if not path.is_dir():
            raise FileNotFoundError(f"Directory not found or not a directory: {path}")
        formats = self._formats
        tracks = [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in formats]
        return sorted(tracks)

    @staticmethod
    def _guard_removable(path: Path) -> None:
        """Fail fast if ``path`` lives on an unmounted removable/network drive."""
        drive = path.drive.upper()
        if drive in _REMOVABLE_DRIVES and not Path(f"{drive}/").exists():
            raise FileNotFoundError(f"Drive not mounted: {drive} (connect the volume and retry)")

    def select(
        self,
        tracks: Sequence[Path],
        selection: str,
        *,
        tty: bool | None = None,
    ) -> list[Path]:
        """Order ``tracks`` per ``selection`` ("random" or "manual")."""
        items = list(tracks)
        if selection == "random":
            self._shuffle(items)
            return items
        return self._select_manual(items, tty=tty)

    def _select_manual(self, tracks: list[Path], *, tty: bool | None) -> list[Path]:
        """Numbered picker; return all tracks when non-interactive or empty."""
        if not self._interactive(tty):
            return tracks
        for index, track in enumerate(tracks, start=1):
            print(f"{index}. {track.name}")
        try:
            reply = self._input("Select tracks (e.g. 1,3,2-4): ").strip()
        except EOFError:
            return tracks
        if not reply:
            return tracks
        chosen = expand_selection(reply, len(tracks))
        return [tracks[i - 1] for i in chosen]

    @staticmethod
    def _interactive(tty: bool | None) -> bool:
        """Decide whether prompting is allowed for this run."""
        if tty is not None:
            return tty
        return sys.stdin.isatty()
