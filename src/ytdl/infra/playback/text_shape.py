"""Text shaping for the title/subtitle tracks: RTL (Hebrew/Arabic) reordering + a
glyph-complete font. The render engines (ffmpeg drawtext, Pillow/MoviePy) draw
LEFT-TO-RIGHT, so right-to-left text is reordered to VISUAL order with python-bidi
before drawing, and a Unicode font (Arial / DejaVu) is used so the glyphs exist.
"""

from __future__ import annotations

import os

from bidi.algorithm import get_display

_FONTS = (
    r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
)


def font_path() -> str:
    """First existing Unicode TTF (has Hebrew/Arabic glyphs); the MoviePy font."""
    return next((f for f in _FONTS if os.path.exists(f)), _FONTS[0])


def _is_rtl(text: str) -> bool:
    return any("֐" <= c <= "׿" or "؀" <= c <= "ۿ" for c in text)


def shape_text(text: str) -> str:
    """Return ``text`` in VISUAL order — RTL reordered, LTR left untouched."""
    return get_display(text) if text and _is_rtl(text) else text


def drawtext_fontfile() -> str:
    """An escaped ``fontfile=...`` drawtext option so all glyphs (incl. Hebrew) render."""
    path = font_path().replace("\\", "/").replace(":", "\\:")
    return f"fontfile='{path}'"
