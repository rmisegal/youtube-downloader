"""Unit tests for RTL text shaping + the drawtext font option."""

from __future__ import annotations

from ytdl.infra.playback.text_shape import drawtext_fontfile, font_path, shape_text


def test_hebrew_is_reordered_to_visual() -> None:
    heb = "שלום"
    shaped = shape_text(heb)
    assert shaped != heb  # reordered to visual order for an LTR engine
    assert set(shaped) == set(heb)  # same letters, different order


def test_latin_is_left_untouched() -> None:
    assert shape_text("HELLO") == "HELLO"
    assert shape_text("") == ""


def test_drawtext_fontfile_is_escaped() -> None:
    spec = drawtext_fontfile()
    assert spec.startswith("fontfile='") and spec.endswith("'")
    assert "\\:" in spec or "/" not in font_path()  # colon escaped on Windows paths


def test_font_path_is_a_ttf() -> None:
    assert font_path().lower().endswith(".ttf")
