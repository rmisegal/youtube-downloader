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
    match = _DURATION_RE.search(getattr(result, "stderr", "") or "")
    if not match:
        return 0.0
    hours, minutes, seconds, centis = (int(g) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds + centis / 100
