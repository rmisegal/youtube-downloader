"""Title/subtitle text overlays (FFmpeg ``drawtext``) for the overlay-TRACKS pass.

Builds ONE ``drawtext`` per text element, applied over the base video, reusing the
shared effect vocabulary: the element's own in/out gate (``enable``), an alpha
in/out **fade** (the shared ``fade`` transition), a **move** by direction, a
beat-synced **pulse** bob (shared BPM math), and a **colour**. Comma-bearing
expressions are single-quoted so the filterchain parses them as one option value.
"""

from __future__ import annotations

from ytdl.constants import TRANSITION_FADE, TRANSITION_PULSE
from ytdl.infra.playback.renderer_graph import _fmt
from ytdl.infra.playback.text_shape import drawtext_fontfile, shape_text

_COLORS = ("white", "yellow", "cyan", "orange", "#FF66CC", "#66FFAA", "#FF5555")
_FADE = 0.4  # seconds of alpha fade in/out


def _escape(text: str) -> str:
    """Escape characters ``drawtext`` treats specially (keep it simple/safe)."""
    return text.replace("\\", "").replace("'", "’").replace(":", " ").replace("%", "")


def _position(at: float, until: float, direction: str, x0: str, y0: str) -> tuple[str, str]:
    """Static (x0,y0) or a moving expression across [at,until] by direction."""
    dur = max(0.001, until - at)
    prog = f"(t-{_fmt(at)})/{_fmt(dur)}"
    direction = (direction or "").strip().lower()
    if direction == "left":  # enter right, exit left
        return f"w-(w+text_w)*{prog}", y0
    if direction == "right":
        return f"-text_w+(w+text_w)*{prog}", y0
    if direction == "up":
        return x0, f"h-(h+text_h)*{prog}"
    if direction == "down":
        return x0, f"-text_h+(h+text_h)*{prog}"
    return x0, y0


def text_drawtext(
    text: str, at: float, until: float, *, canvas: tuple[int, int], effect: str = "",
    transition: str = "", direction: str = "", color: str = "", bpm: float = 0.0,
    x: float | None = None, y: float | None = None, fontsize: int = 0,
) -> str:
    """Return one ``drawtext`` filter for a text element (gated to [at,until])."""
    seed = sum(ord(c) for c in text) + len(text) + 1
    # Spread titles ALL OVER the screen (not just centred) when no x/y is given.
    sx = 0.08 + (seed * 37 % 58) / 100.0
    sy = 0.10 + (seed * 53 % 52) / 100.0
    x0 = f"w*{_fmt(x)}-text_w/2" if x is not None else f"w*{_fmt(round(sx, 3))}-text_w/2"
    y0 = f"h*{_fmt(y)}" if y is not None else f"h*{_fmt(round(sy, 3))}"
    if effect == TRANSITION_PULSE:  # heart-beat bob at the song tempo (shared BPM math)
        f = max(0.1, (bpm or 120.0) / 60.0)
        y0 = f"({y0})-14*abs(sin(PI*{_fmt(f)}*t))"
    # Keep the text fully inside the frame so it is never CUT at the edges/bottom.
    x0 = f"max(8,min({x0},w-text_w-8))"
    y0 = f"max(8,min({y0},h-text_h-8))"
    xx, yy = _position(at, until, direction, x0, y0)
    col = color or _COLORS[seed % len(_COLORS)]
    size = fontsize or (48 + (seed % 6) * 16)
    parts = [
        f"drawtext={drawtext_fontfile()}:text='{_escape(shape_text(text))}'",
        f"x='{xx}'", f"y='{yy}'",
        f"fontsize={size}", f"fontcolor={col}", "borderw=4", "bordercolor=black@0.85",
        f"enable='between(t,{_fmt(at)},{_fmt(until)})'",
    ]
    if transition == TRANSITION_FADE:
        a = (f"if(lt(t,{_fmt(at + _FADE)}),(t-{_fmt(at)})/{_fmt(_FADE)},"
             f"if(gt(t,{_fmt(until - _FADE)}),({_fmt(until)}-t)/{_fmt(_FADE)},1))")
        parts.append(f"alpha='{a}'")
    return ":".join(parts)
