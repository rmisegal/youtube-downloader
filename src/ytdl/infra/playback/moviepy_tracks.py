"""MoviePy text-track renderer for ADVANCED effects ffmpeg drawtext cannot do:
true zoom (scale), 360° rotation, circular/spiral paths, and the per-letter
explode/assemble/raindrop motions. Used only when a title requests such an effect
(the simple effects stay on the fast drawtext path). Renders through the bundled
imageio-ffmpeg; text is drawn by Pillow (no ImageMagick).
"""

from __future__ import annotations

import math
import os
from typing import Any

from ytdl.constants import (
    PER_LETTER_TEXT_EFFECTS,
    TEXT_CIRCLE,
    TEXT_MOVE,
    TEXT_ROTATE,
    TEXT_SPIRALIN,
    TEXT_SPIRALOUT,
    TEXT_ZOOMIN,
    TEXT_ZOOMOUT,
    TRANSITION_FADE,
    TRANSITION_PULSE,
)
from ytdl.infra.playback.text_letters import letter_clips
from ytdl.infra.playback.text_shape import font_path, shape_text
from ytdl.services.analysis.beat_time import resolve_timing

_COLORS = ("yellow", "white", "cyan", "orange", "#FF66CC", "#66FFAA")


def _b(value: float, size: float, extent: float) -> float:
    """Keep a clip FULLY on-screen — MoviePy crashes when a clip leaves the frame."""
    return min(max(value, 0.0), max(0.0, extent - size))


def _anchor(el: Any, w: int, h: int) -> tuple[float, float, float, str, int]:
    seed = sum(ord(c) for c in el.text) + len(el.text) + 1
    ax = el.x * w if el.x is not None else (0.08 + (seed * 37 % 58) / 100.0) * w
    ay = el.y * h if el.y is not None else (0.1 + (seed * 53 % 50) / 100.0) * h
    return ax, ay, el.fontsize or (44 + (seed % 6) * 16), el.color or _COLORS[seed % 6], seed


def _clip(text: str, font: str, size: float, color: str) -> Any:
    from moviepy import TextClip  # noqa: PLC0415 - lazy heavy import

    return TextClip(font=font, text=shape_text(text), font_size=int(size), color=color,
                    stroke_color="black", stroke_width=2)


def _animate(clip: Any, el: Any, at: float, dur: float, w: int, h: int, bpm: float,
             ax: float, ay: float) -> Any:
    eff = (el.effect or "").lower()
    r = min(w, h) * 0.30
    cw, ch = clip.w, clip.h
    pos = (_b(ax, cw, w), _b(ay, ch, h))  # clamp the anchor fully on-screen
    clip = clip.with_start(at).with_duration(dur)
    if eff == TEXT_ZOOMIN:
        return clip.resized(lambda t: max(0.1, min(1.0, t / (dur * 0.5)))).with_position(pos)
    if eff == TEXT_ZOOMOUT:
        return clip.resized(lambda t: max(0.1, 1.3 - t / dur)).with_position(pos)
    if eff == TEXT_ROTATE:  # rotation EXPANDS the bbox -> centre it so it can't leave the frame
        return clip.rotated(lambda t: 360.0 * t / dur).with_position(("center", "center"))
    if eff == TEXT_CIRCLE:
        return clip.with_position(lambda t: (
            _b(ax + r * math.cos(2 * math.pi * t / dur), cw, w),
            _b(ay + r * math.sin(2 * math.pi * t / dur), ch, h)))
    if eff in (TEXT_SPIRALIN, TEXT_SPIRALOUT):
        grow = (lambda t: t / dur) if eff == TEXT_SPIRALOUT else (lambda t: 1 - t / dur)
        return clip.with_position(lambda t: (
            _b(ax + r * grow(t) * math.cos(4 * math.pi * t / dur), cw, w),
            _b(ay + r * grow(t) * math.sin(4 * math.pi * t / dur), ch, h)))
    if eff == TEXT_MOVE:
        d = (el.direction or "left").lower()
        paths = {
            "right": lambda t: (_b(-cw + (w + cw) * t / dur, cw, w), ay),
            "up": lambda t: (ax, _b(h - (h + ch) * t / dur, ch, h)),
            "down": lambda t: (ax, _b(-ch + (h + ch) * t / dur, ch, h)),
        }
        return clip.with_position(paths.get(d, lambda t: (_b(w - (w + cw) * t / dur, cw, w), ay)))
    if eff == TRANSITION_PULSE:
        f = max(0.1, (bpm or 120.0) / 60.0)
        return clip.resized(lambda t: 1.0 + 0.13 * abs(math.sin(math.pi * f * t))).with_position(pos)
    return clip.with_position(pos)


def _element_clips(el: Any, at: float, dur: float, w: int, h: int, font: str, bpm: float) -> list[Any]:
    ax, ay, size, color, seed = _anchor(el, w, h)
    if (el.effect or "").lower() in PER_LETTER_TEXT_EFFECTS:
        clips = letter_clips(el, at, dur, w, h, font, size, color, ax, ay, seed)
    else:
        clips = [_animate(_clip(el.text, font, size, color), el, at, dur, w, h, bpm, ax, ay)]
    if (el.transition or "").lower() == TRANSITION_FADE:
        from moviepy import vfx  # noqa: PLC0415 - lazy heavy import

        fade = min(0.4, dur / 3)
        clips = [c.with_effects([vfx.CrossFadeIn(fade), vfx.CrossFadeOut(fade)]) for c in clips]
    return clips


def render_moviepy_overlay(
    base_file: str, payload: dict, out_file: str, *, canvas: tuple[int, int],
    fps: int, ffmpeg_exe: str,
) -> None:
    """Composite all text-track elements over the base via MoviePy and write the mix."""
    os.environ.setdefault("IMAGEIO_FFMPEG_EXE", ffmpeg_exe)
    from moviepy import CompositeVideoClip, VideoFileClip  # noqa: PLC0415 - lazy heavy import

    w, h = canvas
    font = font_path()
    base = VideoFileClip(base_file)
    layers = [base]
    for el in payload.get("elements", []):
        at, until = resolve_timing(el, payload.get("beats", []), payload.get("total", 0.0))
        if until <= at or not el.text:
            continue
        layers += _element_clips(el, at, until - at, w, h, font, payload.get("bpm", 0.0))
    comp = CompositeVideoClip(layers, size=(w, h)).with_audio(base.audio)
    # ``logger="bar"`` shows a tqdm PROGRESS BAR on the console (the slow MoviePy pass).
    comp.write_videofile(out_file, fps=fps, codec="libx264", audio_codec="aac", logger="bar")
    comp.close()
    base.close()
