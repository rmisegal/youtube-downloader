"""Unit tests for :mod:`ytdl.infra.playback.transitions`."""

from __future__ import annotations

import pytest

from ytdl.constants import IMAGE_TRANSITIONS, TRANSITION_FADE, TRANSITION_RANDOM
from ytdl.infra.playback.transitions import image_vfilter, resolve

CANVAS = (1280, 720)


class _RNG:
    def __init__(self, pick: str) -> None:
        self._pick = pick

    def choice(self, _seq):  # type: ignore[no-untyped-def]
        return self._pick


def test_resolve_random_uses_injected_rng() -> None:
    assert resolve(TRANSITION_RANDOM, rng=_RNG("zoomin")) == "zoomin"


def test_resolve_default_is_random() -> None:
    # empty/None transition behaves as random
    assert resolve("", rng=_RNG("panleft")) == "panleft"


def test_resolve_random_picks_from_supported_set() -> None:
    import random

    rng = random.Random(0)
    for _ in range(20):
        assert resolve("random", rng=rng) in IMAGE_TRANSITIONS


def test_resolve_explicit_name_passthrough() -> None:
    assert resolve("zoomout") == "zoomout"


def test_resolve_pan_plus_direction() -> None:
    assert resolve("pan", "right") == "panright"


def test_resolve_unknown_falls_back_to_fade() -> None:
    assert resolve("sparkle") == TRANSITION_FADE


@pytest.mark.parametrize(
    ("name", "needle"),
    [
        ("zoomin", "zoompan="),
        ("zoomout", "zoompan="),
        ("panleft", "zoompan="),
        ("panright", "zoompan="),
        ("fadeblack", "fade=t=in"),
    ],
)
def test_image_vfilter_contains_expected_filter(name, needle) -> None:
    vf = image_vfilter(name, duration=6.0, canvas=CANVAS, fps=30)
    assert needle in vf
    assert "scale=1280:720" in vf and "crop=1280:720" in vf
    assert vf.endswith("format=yuv420p,settb=AVTB")


def test_only_fadeblack_fades_through_black() -> None:
    # Clean transitions must NOT fade to black (that caused black gaps between slides).
    for name in ("zoomin", "zoomout", "panleft", "pulse", "fade"):
        assert "fade=t=" not in image_vfilter(name, 6.0, CANVAS, 30)
    # The deliberate dramatic transition DOES fade through black.
    assert "fade=t=out" in image_vfilter("fadeblack", 6.0, CANVAS, 30)


def test_pan_directions_differ() -> None:
    left = image_vfilter("panleft", 6.0, CANVAS, 30)
    right = image_vfilter("panright", 6.0, CANVAS, 30)
    assert left != right  # opposite directions produce different x expressions


def test_zoompan_frame_count_scales_with_duration() -> None:
    vf = image_vfilter("zoomin", duration=4.0, canvas=CANVAS, fps=30)
    assert "d=120" in vf  # 4s * 30fps


def test_resolve_recognizes_beat_transitions() -> None:
    from ytdl.infra.playback.transitions import resolve

    assert resolve("pulse") == "pulse"
    assert resolve("shake") == "shake"
    assert resolve("bounce") == "bounce"
    assert resolve("flash") == "flash"


def test_image_vfilter_beat_effect_uses_zoompan_and_bpm() -> None:
    vf = image_vfilter("pulse", 4.0, CANVAS, 30, bpm=120.0)
    assert "zoompan" in vf and "format=yuv420p" in vf and "sin" in vf
