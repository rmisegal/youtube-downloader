"""Unit tests for the title/subtitle drawtext builder (string assertions)."""

from __future__ import annotations

from ytdl.infra.playback.titles import text_drawtext

CANVAS = (1280, 720)


def test_basic_text_and_enable_gate() -> None:
    s = text_drawtext("HELLO", 1.0, 5.0, canvas=CANVAS)
    assert s.startswith("drawtext=fontfile=") and "text='HELLO'" in s  # font for Hebrew glyphs
    assert "enable='between(t,1,5)'" in s


def test_text_stays_inside_the_frame() -> None:
    # y is clamped so the text is never cut off the bottom/edges.
    s = text_drawtext("LOW", 0.0, 4.0, canvas=CANVAS, y=0.98)
    assert "min(" in s and "h-text_h" in s


def test_move_left_uses_progress_expression() -> None:
    s = text_drawtext("HI", 0.0, 4.0, canvas=CANVAS, direction="left")
    assert "w-(w+text_w)*" in s  # slides right -> left


def test_pulse_bobs_at_bpm() -> None:
    s = text_drawtext("HI", 0.0, 4.0, canvas=CANVAS, effect="pulse", bpm=120.0)
    assert "sin(" in s  # beat-synced bob


def test_fade_transition_adds_alpha() -> None:
    s = text_drawtext("HI", 0.0, 4.0, canvas=CANVAS, transition="fade")
    assert "alpha='" in s


def test_color_size_and_position() -> None:
    s = text_drawtext("HI", 0.0, 4.0, canvas=CANVAS, color="red", x=0.1, y=0.2, fontsize=50)
    assert "fontcolor=red" in s and "fontsize=50" in s and "w*0.1" in s
