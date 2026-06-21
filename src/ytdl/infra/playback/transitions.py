"""Per-image transition/animation FFmpeg filters (PRD-images §4).

Turns a still image (looped to a clip of ``duration`` seconds) into an animated
clip on the common canvas: a Ken-Burns ``zoompan`` (zoom in/out, pan with a
direction), a beat-reactive effect, or a static hold. Clips fill the frame for
their whole slot — only the deliberate ``fadeblack`` transition fades through
black — so contiguous slides flow without a black gap. ``resolve`` expands
``"random"`` (default) via an injectable RNG so tests are deterministic.
"""

from __future__ import annotations

import random as _random
from typing import Any

from ytdl.constants import (
    ALL_TRANSITIONS,
    BEAT_TRANSITIONS,
    IMAGE_TRANSITIONS,
    TRANSITION_FADE,
    TRANSITION_FADEBLACK,
    TRANSITION_PANDOWN,
    TRANSITION_PANLEFT,
    TRANSITION_PANRIGHT,
    TRANSITION_PANUP,
    TRANSITION_RANDOM,
    TRANSITION_ZOOMIN,
    TRANSITION_ZOOMOUT,
)
from ytdl.infra.playback.beat_effects import beat_animation
from ytdl.infra.playback.renderer_graph import _fmt

_EDGE_FADE_MAX = 0.5  # seconds


def resolve(transition: str, direction: str = "", *, rng: Any = _random) -> str:
    """Return a concrete transition name (expands ``random``; ``pan`` + direction).

    ``random`` resolves to a STATIC transition only (beat-reactive effects need a
    tempo, so they are opt-in via the music-sync placer or an explicit name).
    """
    name = (transition or TRANSITION_RANDOM).strip().lower()
    if name == TRANSITION_RANDOM:
        return rng.choice(IMAGE_TRANSITIONS)
    if name == "pan" and direction:
        name = "pan" + direction.strip().lower()
    return name if name in ALL_TRANSITIONS else TRANSITION_FADE


def image_vfilter(
    transition: str, duration: float, canvas: tuple[int, int], fps: int, bpm: float = 0.0
) -> str:
    """Build the ``-vf`` chain for an animated image clip of ``duration`` seconds.

    ``bpm`` (when > 0) drives the beat-reactive effects so they throb in time with
    the soundtrack. Only the deliberate ``fadeblack`` transition fades through BLACK
    (for dramatic section changes); every other transition fills the frame for its
    whole slot, so contiguous slides flow WITHOUT a black gap between them.
    """
    w, h = canvas
    base = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
    if transition == TRANSITION_FADEBLACK:
        anim, fade = "", _edge_fade(duration)
    else:
        anim, fade = _animation(transition, duration, w, h, fps, bpm), ""
    parts = [base, anim, fade, f"fps={fps}", "format=yuv420p", "settb=AVTB"]
    return ",".join(p for p in parts if p)


def _edge_fade(duration: float) -> str:
    """Short fade-in + fade-out so overlapping timeline clips blend."""
    d = min(_EDGE_FADE_MAX, duration / 4) if duration > 0 else 0.0
    if d <= 0:
        return ""
    out_st = max(0.0, duration - d)
    return f"fade=t=in:st=0:d={_fmt(d)},fade=t=out:st={_fmt(out_st)}:d={_fmt(d)}"


def _animation(name: str, duration: float, w: int, h: int, fps: int, bpm: float = 0.0) -> str:
    """The ``zoompan`` expression for a transition (``""`` for plain fade)."""
    frames = max(1, round(duration * fps))
    if name in BEAT_TRANSITIONS:
        return beat_animation(name, frames, w, h, fps, bpm)
    centre_x, centre_y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if name == TRANSITION_ZOOMIN:
        spec = ("z='min(zoom+0.0015,1.5)'", centre_x, centre_y)
    elif name == TRANSITION_ZOOMOUT:
        spec = ("z='if(eq(on,1),1.5,max(zoom-0.0015,1.0))'", centre_x, centre_y)
    elif name in (TRANSITION_PANLEFT, TRANSITION_PANRIGHT, TRANSITION_PANUP, TRANSITION_PANDOWN):
        spec = _pan(name, frames)
    else:
        return ""  # fade / unknown -> no zoompan
    z, x, y = spec
    return f"zoompan={z}:x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps}"


def _pan(name: str, frames: int) -> tuple[str, str, str]:
    """A gentle constant-zoom pan across the image in the given direction."""
    z = "z='1.2'"
    prog = f"on/{frames}"
    span_x, span_y = "(iw-iw/zoom)", "(ih-ih/zoom)"
    centre_x, centre_y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if name == TRANSITION_PANRIGHT:
        return z, f"{span_x}*{prog}", centre_y
    if name == TRANSITION_PANLEFT:
        return z, f"{span_x}*(1-{prog})", centre_y
    if name == TRANSITION_PANDOWN:
        return z, centre_x, f"{span_y}*{prog}"
    return z, centre_x, f"{span_y}*(1-{prog})"  # panup
