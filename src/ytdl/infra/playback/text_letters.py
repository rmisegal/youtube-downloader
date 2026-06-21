"""Per-letter MoviePy text clips: explode / assemble-from-all-sides / raindrop fall.

The word is split into one :class:`TextClip` per letter, each given its own
time-varying ``with_position`` so the letters fly apart (explode), converge from
random edges into the word (assemble), or fall from above one after another (rain).
Closures bind loop values via default args (no late-binding bug).
"""

from __future__ import annotations

import math
from typing import Any

from ytdl.constants import TEXT_ASSEMBLE, TEXT_EXPLODE
from ytdl.infra.playback.text_shape import shape_text

_ADV = 0.62  # per-letter advance as a fraction of font size


def _b(value: float, size: float, extent: float) -> float:
    """Keep a clip FULLY on-screen — MoviePy crashes when a clip leaves the frame."""
    return min(max(value, 0.0), max(0.0, extent - size))


def _letter(font: str, ch: str, size: float, color: str) -> Any:
    from moviepy import TextClip  # noqa: PLC0415 - lazy heavy import

    return TextClip(font=font, text=ch, font_size=int(size), color=color,
                    stroke_color="black", stroke_width=2)


def letter_clips(
    el: Any, at: float, dur: float, w: int, h: int, font: str, size: float,
    color: str, ax: float, ay: float, seed: int,
) -> list[Any]:
    """Return a positioned per-letter clip list for the element's effect."""
    eff = (el.effect or "").lower()
    chars = list(shape_text(el.text))  # RTL reordered to visual order before splitting
    adv = size * _ADV
    x0 = ax - max(1, len(chars)) * adv / 2.0
    out: list[Any] = []
    for i, ch in enumerate(chars):
        if ch == " ":
            continue
        fx, fy = x0 + i * adv, ay
        ang = math.radians((seed * (i + 1) * 97) % 360)
        clip = _letter(font, ch, size, color).with_start(at).with_duration(dur)
        if eff == TEXT_EXPLODE:                       # hold, then fly outward (to the edges)
            dx, dy = math.cos(ang) * w, math.sin(ang) * h
            clip = clip.with_position(lambda t, fx=fx, fy=fy, dx=dx, dy=dy, dur=dur, sz=size: (
                _b(fx + dx * max(0.0, t / dur - 0.5), sz, w),
                _b(fy + dy * max(0.0, t / dur - 0.5), sz, h)))
        elif eff == TEXT_ASSEMBLE:                    # fly in from the edges
            sx, sy = ax + math.cos(ang) * w, ay + math.sin(ang) * h
            clip = clip.with_position(lambda t, fx=fx, fy=fy, sx=sx, sy=sy, dur=dur, sz=size: (
                _b(sx + (fx - sx) * min(1.0, t / (dur * 0.6)), sz, w),
                _b(sy + (fy - sy) * min(1.0, t / (dur * 0.6)), sz, h)))
        else:                                         # rain: fall from the top, staggered
            delay = i * 0.07 * dur
            clip = clip.with_position(lambda t, fx=fx, fy=fy, d=delay, dur=dur, sz=size: (
                _b(fx, sz, w),
                _b(-sz + (fy + sz) * min(1.0, max(0.0, (t - d) / (dur * 0.45))), sz, h)))
        out.append(clip)
    return out
