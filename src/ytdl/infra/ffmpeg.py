"""FfmpegLocator: resolve the bundled FFmpeg executable (no system FFmpeg).

Mirrors the transcribe-video pattern: when configured location is ``"auto"`` the
binary shipped with the ``imageio-ffmpeg`` pip package is used via
``imageio_ffmpeg.get_ffmpeg_exe()``. An explicit path bypasses that import.
yt-dlp's ``ffmpeg_location`` wants the *directory*, exposed via :meth:`exe_dir`.
"""

from __future__ import annotations

import os

# Sentinel meaning "auto-resolve via imageio_ffmpeg" (matches config default).
AUTO_LOCATION = "auto"


class FfmpegLocator:
    """Resolves (and memoizes) the FFmpeg executable path.

    Args:
        location: Either ``"auto"`` (resolve via ``imageio_ffmpeg``) or an
            explicit path to an ffmpeg executable. ``None`` falls back to
            ``"auto"``.
    """

    def __init__(self, location: str | None = None) -> None:
        self._location: str = location or AUTO_LOCATION
        self._resolved: str | None = None

    def exe(self) -> str:
        """Return the ffmpeg executable path, resolving once and caching it."""
        if self._resolved is None:
            self._resolved = self._resolve()
        return self._resolved

    def exe_dir(self) -> str:
        """Return the parent directory of :meth:`exe` (yt-dlp ``ffmpeg_location``)."""
        return os.path.dirname(self.exe())

    def _resolve(self) -> str:
        """Compute the executable path from config or the bundled binary."""
        if self._location != AUTO_LOCATION:
            return self._location
        # Lazy import so the dependency is only loaded when actually needed
        # and so tests can patch ``imageio_ffmpeg.get_ffmpeg_exe``.
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
