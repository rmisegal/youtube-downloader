"""``MixSegment`` value object — shared per-clip timing currency (PRD-playlist §2).

The sampler, ``--play-for-sec``, and YAML playlist members each produce
``list[MixSegment]``; engines and the ``MixRenderer`` consume them.
"""

from __future__ import annotations

from dataclasses import dataclass

from ytdl.constants import EFFECT_FADE


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
    """

    path: str
    start: float = 0.0
    play_seconds: float | None = None
    speed: float = 1.0
    resolution: str = "max"
    subtitle: str | bool | None = None
    effect: str = EFFECT_FADE
