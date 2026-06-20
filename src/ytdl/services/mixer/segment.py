"""``MixSegment`` value object — shared per-clip timing currency (PRD-playlist §2).

The sampler, ``--play-for-sec``, and YAML playlist members each produce
``list[MixSegment]``; engines and the ``MixRenderer`` consume them.
"""

from __future__ import annotations

from dataclasses import dataclass

from ytdl.constants import EFFECT_FADE, MEMBER_VIDEO, TRANSITION_RANDOM


@dataclass(frozen=True)
class MixSegment:
    """Immutable description of one clip's contribution to a mix (PRD §2).

    Acts as the common currency between segment builders (sampler /
    ``--play-for-sec`` / YAML members) and consumers (engines / renderer).

    Attributes:
        path: Source file path (or resolved URL cache path).
        start: In-point in seconds (``-ss``).
        play_seconds: Seconds to play before the crossfade; ``None`` = full clip.
        speed: Playback speed multiplier (``1.0`` = normal).
        resolution: ``"max"`` or a ``"WxH"`` / height string.
        subtitle: ``None``/``False`` = off, ``True`` = embedded, ``"<file>"`` = insert.
        effect: Transition / mix effect name (defaults to ``"fade"``).
        kind: ``"video"`` (default) or ``"image"`` — an image is looped + animated.
        transition: per-image animation name or ``"random"`` (default) — see
            :mod:`ytdl.infra.playback.transitions`. Ignored for video.
        direction: optional pan/move direction (``left|right|up|down``) for images.
        at: absolute timeline start (seconds) for timeline placement; ``None`` = sequential.
        until: absolute timeline end (seconds) for images; image duration = ``until - at``.
        bpm: music tempo for beat-reactive effects (pulse/shake/…); ``0`` = default 120.
    """

    path: str
    start: float = 0.0
    play_seconds: float | None = None
    speed: float = 1.0
    resolution: str = "max"
    subtitle: str | bool | None = None
    effect: str = EFFECT_FADE
    kind: str = MEMBER_VIDEO
    transition: str = TRANSITION_RANDOM
    direction: str = ""
    at: float | None = None
    until: float | None = None
    bpm: float = 0.0
