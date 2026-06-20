"""Unit tests for beat-reactive image effects (filter-string assertions)."""

from __future__ import annotations

from ytdl.infra.playback.beat_effects import beat_animation


def test_pulse_is_bpm_driven_zoompan() -> None:
    f = beat_animation("pulse", 120, 1280, 720, 30, 120.0)
    assert "zoompan" in f and "sin" in f and "abs" in f
    assert "*2*" in f or "2*on" in f or "*2/" in f or "2)" in f  # 120bpm -> 2 beats/sec


def test_shake_oscillates_both_axes() -> None:
    f = beat_animation("shake", 120, 1280, 720, 30, 120.0)
    assert "zoompan" in f and "sin" in f and "cos" in f


def test_bounce_is_zoompan() -> None:
    assert "zoompan" in beat_animation("bounce", 60, 800, 600, 30, 100.0)


def test_flash_adds_brightness_eq() -> None:
    f = beat_animation("flash", 60, 800, 600, 30, 100.0)
    assert "zoompan" in f and "eq=brightness" in f and "eval=frame" in f


def test_unknown_effect_is_empty() -> None:
    assert beat_animation("nope", 60, 800, 600, 30, 120.0) == ""


def test_zero_bpm_falls_back_to_default() -> None:
    assert "zoompan" in beat_animation("pulse", 60, 800, 600, 30, 0.0)
