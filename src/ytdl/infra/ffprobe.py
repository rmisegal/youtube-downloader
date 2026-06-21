"""Provide an ffmpeg+ffprobe directory for yt-dlp **section** downloads.

The bundled ``imageio-ffmpeg`` ships ffmpeg only; yt-dlp's partial/``download_ranges``
feature also needs **ffprobe**. ``static-ffmpeg`` fetches both (once, cached). Resolving
is lazy and best-effort: if it can't be fetched (offline), callers fall back to a full
download. Only used by the movie pipeline's section fetch — normal downloads keep using
the bundled binary.
"""

from __future__ import annotations

import os

_cached: str | None = None  # None = not tried; "" = tried + unavailable


def ffmpeg_dir_with_probe() -> str | None:
    """Return a directory holding both ``ffmpeg`` and ``ffprobe``, or ``None``."""
    global _cached
    if _cached is not None:
        return _cached or None
    try:
        import static_ffmpeg
        from static_ffmpeg import run
        # yt-dlp's partial-download gate (FFmpegFD.available) checks PATH, not the
        # ffmpeg_location opt — so put ffmpeg+ffprobe on PATH, not just return the dir.
        static_ffmpeg.add_paths()
        ffmpeg_path, _ffprobe = run.get_or_fetch_platform_executables_else_raise()
        _cached = os.path.dirname(ffmpeg_path)
    except Exception:  # noqa: BLE001 - any fetch/import failure → graceful fallback
        _cached = ""
    return _cached or None
