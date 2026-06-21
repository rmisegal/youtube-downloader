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

    def ytdlp_location(self) -> str:
        """A path yt-dlp accepts as ffmpeg — its basename must be ``ffmpeg``.

        The bundled imageio-ffmpeg binary has a non-standard name
        (``ffmpeg-win-x86_64-v7.1.exe``) that yt-dlp rejects for partial/section
        downloads. Ensure a correctly-named sibling exists (a free hardlink, copy
        fallback) and return it; otherwise return the original.
        """
        exe = self.exe()
        if os.path.splitext(os.path.basename(exe))[0].lower() in ("ffmpeg", "avconv"):
            return exe
        target = os.path.join(os.path.dirname(exe), "ffmpeg" + (".exe" if os.name == "nt" else ""))
        if not os.path.exists(target):
            try:
                os.link(exe, target)
            except OSError:
                import shutil
                try:
                    shutil.copy2(exe, target)
                except OSError:
                    return exe
        return target

    def _resolve(self) -> str:
        """Compute the executable path from config or the bundled binary."""
        if self._location != AUTO_LOCATION:
            return self._location
        # Lazy import so the dependency is only loaded when actually needed
        # and so tests can patch ``imageio_ffmpeg.get_ffmpeg_exe``.
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
