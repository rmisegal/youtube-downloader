"""Crossfade-looped leading audio (PRD-playlist §6 — clean loop for short songs).

When the leading song is SHORTER than the video mix, a hard ``-stream_loop`` seam
is audible. Instead we pre-render an audio file that loops the song with an
``acrossfade`` at each seam (the end of the song dissolves into its beginning),
long enough to cover the video. The main render then trims it to the video length
and fades it out. Kept separate so :mod:`renderer` stays ≤150 code lines.
"""

from __future__ import annotations

import math

_AAC = "aac"


def _fmt(value: float) -> str:
    """Format a duration compactly (no trailing ``.0``)."""
    return str(int(value)) if float(value).is_integer() else f"{value:.3f}"


def loop_copies(audio_seconds: float, video_seconds: float, crossfade: float) -> int:
    """How many song copies to acrossfade-chain to cover ``video_seconds``.

    Returns ``0`` when no loop is needed/possible: the song already covers the
    video (``audio >= video``), a degenerate input, or the song is too short to
    crossfade (``audio <= crossfade`` — the caller falls back to a hard loop).
    With ``k`` copies the chain lasts ``k·audio − (k−1)·crossfade``.
    """
    if audio_seconds <= 0 or video_seconds <= 0 or audio_seconds >= video_seconds:
        return 0
    if audio_seconds <= crossfade:
        return 0
    needed = (video_seconds - crossfade) / (audio_seconds - crossfade)
    return max(2, math.ceil(needed))


def build_loop_command(
    ffmpeg_exe: str,
    leading_path: str,
    copies: int,
    crossfade: float,
    out_path: str,
) -> list[str]:
    """Build the ffmpeg argv that acrossfade-chains ``copies`` of the song.

    Each seam is an ``acrossfade`` (clean dissolve) rather than a hard cut; the
    result lasts ``copies·audio − (copies−1)·crossfade`` seconds.
    """
    inputs: list[str] = []
    for _ in range(copies):
        inputs += ["-i", leading_path]
    steps: list[str] = []
    current = "0"
    for i in range(1, copies):
        label = "aout" if i == copies - 1 else f"al{i}"
        steps.append(f"[{current}][{i}]acrossfade=d={_fmt(crossfade)}[{label}]")
        current = label
    return [
        ffmpeg_exe, "-nostdin", "-y",
        *inputs,
        "-filter_complex", ";".join(steps),
        "-map", "[aout]",
        "-c:a", _AAC,
        out_path,
    ]
