"""Overlay-track value objects — independent, timed text elements (titles/subtitles).

A :class:`TrackElement` is one piece of text with its OWN timeline (``at_beat`` +
``for_beats``, or ``at``/``until`` seconds), its own in/out ``transition``, ``effect``
(shared vocabulary), ``direction`` (move), ``color`` and optional ``x``/``y`` (0..1).
:class:`Tracks` groups them into the title + subtitle overlay tracks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackElement:
    """One text element on an overlay track (its own beat-timeline + effects)."""

    text: str = ""
    at_beat: int | None = None
    for_beats: int | None = None
    at: float | None = None
    until: float | None = None
    effect: str = ""        # shared effect name (e.g. pulse) — heart-beat bob on text
    transition: str = ""    # in/out transition (e.g. fade -> alpha fade)
    direction: str = ""     # move direction: left | right | up | down
    color: str = ""
    x: float | None = None  # 0..1 fraction of width (default centred)
    y: float | None = None  # 0..1 fraction of height
    fontsize: int = 0


@dataclass(frozen=True)
class Tracks:
    """The overlay tracks (``metadata.tracks``) — each its own independent timeline."""

    titles: tuple[TrackElement, ...] = ()
    subtitles: tuple[TrackElement, ...] = ()

    def all_elements(self) -> list[TrackElement]:
        """Every overlay element (titles then subtitles) — z-order bottom→top."""
        return [*self.titles, *self.subtitles]

    def is_empty(self) -> bool:
        """True when there are no overlay-track elements."""
        return not self.titles and not self.subtitles
