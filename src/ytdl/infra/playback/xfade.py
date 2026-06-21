"""Crossfade (cross-dissolve) renderer for contiguous music-sync timelines.

An opt-in alternative to the fast concat path: instead of clean cuts, adjacent
slides **cross-dissolve** into one another with **no black** (ffmpeg ``xfade`` with
``transition=fade`` is a dissolve, not a fade-through-black). Each clip is padded
by the dissolve duration with its frozen last frame (``tpad``) so the overlap does
NOT shrink the total / break beat alignment — clip *i* still owns its full slot and
then dissolves over the boundary. This re-encodes (slower than concat), which is the
documented trade-off for soft transitions. Mirrors :mod:`timeline`/:mod:`concat`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ytdl.constants import LEADING_AUDIO
from ytdl.infra.playback.renderer_graph import _fmt
from ytdl.services.mixer.segment import MixSegment


def build_xfade_command(
    renderer: Any,
    segments: Sequence[MixSegment],
    *,
    total: float,
    leading_path: str | None,
    leading_kind: str,
    dissolve: float,
    crossfade: float,
    output_path: str,
) -> list[str]:
    """Cross-dissolve the prepped clips over ``dissolve`` seconds; lay the song over it."""
    ordered = sorted(segments, key=lambda s: s.at or 0.0)
    audio = bool(leading_path) and leading_kind == LEADING_AUDIO
    inputs: list[str] = []
    if audio:
        inputs += ["-stream_loop", "-1", "-i", leading_path]  # input 0 = soundtrack
    first = 1 if audio else 0
    for seg in ordered:
        inputs += ["-i", seg.path]

    steps: list[str] = []
    for i, _seg in enumerate(ordered):
        # Freeze the last frame for ``dissolve`` s so the crossfade overlap is free.
        steps.append(f"[{first + i}:v]tpad=stop_mode=clone:stop_duration={_fmt(dissolve)}[c{i}]")
    prev = "c0"
    offset = float(ordered[0].play_seconds or 0.0)
    for i in range(1, len(ordered)):
        out = f"vx{i}"
        steps.append(
            f"[{prev}][c{i}]xfade=transition=fade:duration={_fmt(dissolve)}:"
            f"offset={_fmt(offset)}[{out}]"
        )
        prev = out
        offset += float(ordered[i].play_seconds or 0.0)

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
        *maps, "-t", _fmt(total),
        *renderer._codec_out(output_path),
    ]
