"""Sequential concat renderer for contiguous (music-synced) timelines.

When timeline clips are back-to-back and non-overlapping — the music-sync case,
where each member fills one cut-to-cut slot — concatenating the prepped uniform
``.ts`` clips reproduces the EXACT timeline at a fraction of the cost of the
N-input overlay compositor: the video is stream-**copied** (no re-encode), so a
song with hundreds of cuts renders in seconds. The leading song is laid over the
whole span (looped/trimmed + faded). The caller falls back to the overlay
compositor when clips overlap (manual timelines).

Mirrors :mod:`timeline` — takes the :class:`MixRenderer` for ffmpeg/codec helpers.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ytdl.constants import LEADING_AUDIO
from ytdl.infra.playback.renderer_graph import _fmt
from ytdl.services.mixer.segment import MixSegment

_GAP_TOL = 0.05  # seconds — slots within this of back-to-back count as contiguous


def is_contiguous(segments: Sequence[MixSegment]) -> bool:
    """True when every clip is placed (``at``), starts at ~0, and is back-to-back."""
    placed = [s for s in segments if s.at is not None]
    if not placed or len(placed) != len(segments):
        return False
    ordered = sorted(placed, key=lambda s: s.at or 0.0)
    if (ordered[0].at or 0.0) > _GAP_TOL:  # a leading gap would desync video vs audio
        return False
    for a, b in zip(ordered, ordered[1:], strict=False):
        end = (a.at or 0.0) + (a.play_seconds or 0.0)
        if abs((b.at or 0.0) - end) > _GAP_TOL:  # gap or overlap -> needs the compositor
            return False
    return True


def _write_list(segments: Sequence[MixSegment], tmp_dir: str) -> str:
    """Write a concat-demuxer list file (clips in timeline order); return its path."""
    ordered = sorted(segments, key=lambda s: s.at or 0.0)
    list_path = str(Path(tmp_dir) / "concat.txt")
    with open(list_path, "w", encoding="utf-8") as handle:
        for seg in ordered:
            resolved = str(Path(seg.path).resolve()).replace("'", "'\\''")
            handle.write(f"file '{resolved}'\n")
    return list_path


def build_concat_command(
    renderer: Any,
    segments: Sequence[MixSegment],
    *,
    total: float,
    leading_path: str | None,
    leading_kind: str,
    crossfade: float,
    output_path: str,
    tmp_dir: str,
) -> list[str]:
    """Concat the prepped clips (video copy) + lay the leading soundtrack over it."""
    list_path = _write_list(segments, tmp_dir)
    cmd = [
        renderer._ffmpeg.exe(), "-nostdin", "-y",
        "-f", "concat", "-safe", "0", "-i", list_path,
    ]
    if leading_path and leading_kind == LEADING_AUDIO:
        fade_start = max(0.0, total - crossfade)
        cmd += [
            "-stream_loop", "-1", "-i", leading_path,
            "-filter_complex",
            f"[1:a]atrim=0:{_fmt(total)},"
            f"afade=t=out:st={_fmt(fade_start)}:d={_fmt(crossfade)}[aout]",
            "-map", "0:v:0", "-map", "[aout]", "-c:a", "aac",
        ]
    else:
        cmd += ["-map", "0:v:0"]
    cmd += ["-c:v", "copy", "-t", _fmt(total), output_path]
    return cmd
