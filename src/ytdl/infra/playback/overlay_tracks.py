"""Overlay-tracks pass: composite the title/subtitle text tracks over the base.

A light SECOND render pass — the visual base (images/video + leading audio) is
already rendered; this draws each overlay-track text element on top with its OWN
timeline (``enable`` gate), in/out fade, move and beat effect (see :mod:`titles`),
preserving the base audio. Each element resolves its beat/second timing via
:func:`resolve_timing`. Returns ``None`` when nothing draws (caller keeps the base).
"""

from __future__ import annotations

from typing import Any

from ytdl.infra.playback.titles import text_drawtext
from ytdl.services.analysis.beat_time import resolve_timing


def build_overlay_command(
    renderer: Any, base_file: str, payload: dict, output_path: str
) -> list[str] | None:
    """Build the ffmpeg command drawing all overlay-track elements over ``base_file``."""
    beats = payload.get("beats", [])
    total = float(payload.get("total", 0.0))
    bpm = float(payload.get("bpm", 0.0))
    canvas = renderer._canvas
    chain: list[str] = []
    for el in payload.get("elements", []):
        at, until = resolve_timing(el, beats, total)
        if until <= at or not el.text:
            continue
        chain.append(text_drawtext(
            el.text, at, until, canvas=canvas, effect=el.effect, transition=el.transition,
            direction=el.direction, color=el.color, bpm=bpm, x=el.x, y=el.y,
            fontsize=el.fontsize,
        ))
    if not chain:
        return None
    return [
        renderer._ffmpeg.exe(), "-nostdin", "-y", "-i", base_file,
        "-vf", ",".join(chain),
        *renderer._codec_out(output_path),
    ]
