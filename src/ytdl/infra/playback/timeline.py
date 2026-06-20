"""Absolute-timeline overlay compositor (PRD-images §6).

Places each prepped clip on a black canvas at its absolute ``at`` time via
``setpts`` + ``overlay=enable='between(t,at,until)'`` (later members overlay on
top, so images sit over running video), and lays the leading-audio soundtrack
over the whole span (trimmed + faded; the caller pre-loops a short song).

Mirrors :mod:`renderer_leading`: it takes the :class:`MixRenderer` for its
ffmpeg/canvas/codec helpers, so there is no duplicated config.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ytdl.constants import LEADING_AUDIO
from ytdl.infra.playback.renderer_graph import _fmt
from ytdl.services.mixer.segment import MixSegment


def timeline_total(segments: Sequence[MixSegment]) -> float:
    """The visual span = max(at + duration) across the placed clips."""
    return max(((s.at or 0.0) + (s.play_seconds or 0.0) for s in segments), default=0.0)


def build_timeline_command(
    renderer: Any,
    segments: Sequence[MixSegment],
    *,
    total: float,
    leading_path: str | None,
    leading_kind: str,
    crossfade: float,
    output_path: str,
) -> list[str]:
    """Composite ``segments`` onto a black canvas at their absolute times + audio."""
    w, h = renderer._canvas
    fps = renderer._fps
    audio = bool(leading_path) and leading_kind == LEADING_AUDIO
    inputs: list[str] = []
    if audio:
        inputs += ["-stream_loop", "-1", "-i", leading_path]  # input 0 = soundtrack
    clip0 = 1 if audio else 0
    for seg in segments:
        inputs += ["-i", seg.path]

    steps = [f"color=c=black:s={w}x{h}:r={fps}:d={_fmt(total)}[bg]"]
    prev = "bg"
    for n, seg in enumerate(segments):
        at = seg.at or 0.0
        end = at + (seg.play_seconds or 0.0)
        steps.append(f"[{clip0 + n}:v]setpts=PTS+{_fmt(at)}/TB[c{n}]")
        out = f"o{n}"
        steps.append(
            f"[{prev}][c{n}]overlay=eof_action=pass:"
            f"enable='between(t,{_fmt(at)},{_fmt(end)})'[{out}]"
        )
        prev = out

    maps = ["-map", f"[{prev}]"]
    if audio:
        fade_start = max(0.0, total - crossfade)
        steps.append(
            f"[0:a]atrim=0:{_fmt(total)},"
            f"afade=t=out:st={_fmt(fade_start)}:d={_fmt(crossfade)}[aout]"
        )
        maps += ["-map", "[aout]"]
    return [
        renderer._ffmpeg.exe(), "-nostdin", "-y",
        *inputs,
        "-filter_complex", ";".join(steps),
        *maps,
        *renderer._codec_out(output_path),
    ]
