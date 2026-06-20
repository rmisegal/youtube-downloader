"""Probe a media file's duration via the bundled FFmpeg (no ffprobe needed).

Parses ``Duration: HH:MM:SS.cc`` from ``ffmpeg -i`` stderr — the same approach the
transcribe-video project uses. The subprocess runner is injectable so unit tests
never spawn a real process.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from typing import Any

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)")


def probe_duration(
    path: str,
    ffmpeg_exe: str,
    runner: Callable[..., Any] = subprocess.run,
) -> float:
    """Return ``path``'s duration in seconds (0.0 if it cannot be determined)."""
    # Force UTF-8 with replacement: ffmpeg stderr (banner, filenames) often
    # contains bytes that are not decodable in the Windows console code page
    # (cp1252), which otherwise crashes subprocess's text-mode reader threads.
    result = runner(
        [ffmpeg_exe, "-i", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return _duration_from_stderr(getattr(result, "stderr", "") or "")


def _duration_from_stderr(stderr: str) -> float:
    """Parse ``Duration: HH:MM:SS.cc`` from ffmpeg stderr (0.0 if absent)."""
    match = _DURATION_RE.search(stderr)
    if not match:
        return 0.0
    hours, minutes, seconds, centis = (int(g) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds + centis / 100


def probe_media(
    path: str,
    ffmpeg_exe: str,
    runner: Callable[..., Any] = subprocess.run,
) -> tuple[float, bool]:
    """Return ``(duration_seconds, has_audio)`` parsed from ``ffmpeg -i`` stderr.

    ``has_audio`` is ``True`` when the stderr report lists an ``Audio:`` stream.
    Uses the same UTF-8-with-replacement decoding as :func:`probe_duration` so
    undecodable console-codepage bytes never crash the reader threads.
    """
    result = runner(
        [ffmpeg_exe, "-i", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stderr = getattr(result, "stderr", "") or ""
    return _duration_from_stderr(stderr), "Audio:" in stderr
