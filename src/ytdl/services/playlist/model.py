"""Playlist dataclasses: Playlist / Metadata / Output / Mix / Leading / Member.

Immutable value objects mirroring the YAML playlist schema (PRD-playlist §5.2),
plus the Phase 5.4 selection accessors (pure reads used by the loader / SDK).
Parsed from the YAML playlist by ``loader.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ytdl.constants import (
    EFFECT_FADE,
    LEADING_NONE,
    MIX_AUDIO,
    MIX_STREAMS,
    MIX_SUBTITLE,
    MIX_VIDEO,
    OUTPUT_DISPLAY,
    OUTPUT_MODES,
    OUTPUT_SAVE,
    OUTPUT_STREAM,
)


@dataclass(frozen=True)
class Member:
    """One playlist member (a single clip), ordered by ``id`` (PRD §5.2)."""

    id: int
    file: str
    start_time: float = 0.0
    play_time: float | None = None
    playback_speed: float = 1.0
    resolution: str = "max"
    subtitle: str | bool | None = None
    effect: str = EFFECT_FADE


@dataclass(frozen=True)
class Leading:
    """Leading-track selector (``metadata.leading``) — none | video | audio."""

    kind: str = LEADING_NONE
    file: str = ""


@dataclass(frozen=True)
class MixToggles:
    """Per-stream mix toggles (``metadata.mix``); an off toggle is not produced."""

    video: bool = True
    audio: bool = True
    subtitle: bool = False


@dataclass(frozen=True)
class Output:
    """Output-routing toggles (``metadata.output``) — any combination is valid."""

    display: bool = True
    save: bool = False
    stream: bool = False


@dataclass(frozen=True)
class Metadata:
    """Playlist metadata block (``metadata``) (PRD §5.2)."""

    source_folder: str = ""
    target_folder: str = ""
    output: Output = field(default_factory=Output)
    mix: MixToggles = field(default_factory=MixToggles)
    leading: Leading = field(default_factory=Leading)
    loop: bool = True

    def active_outputs(self) -> list[str]:
        """Enabled output modes, ordered as :data:`OUTPUT_MODES`."""
        enabled = {
            OUTPUT_DISPLAY: self.output.display,
            OUTPUT_SAVE: self.output.save,
            OUTPUT_STREAM: self.output.stream,
        }
        return [mode for mode in OUTPUT_MODES if enabled[mode]]

    def active_mix_streams(self) -> list[str]:
        """Enabled mix streams, ordered as :data:`MIX_STREAMS` (off = excluded)."""
        enabled = {
            MIX_VIDEO: self.mix.video,
            MIX_AUDIO: self.mix.audio,
            MIX_SUBTITLE: self.mix.subtitle,
        }
        return [stream for stream in MIX_STREAMS if enabled[stream]]

    def leading_kind(self) -> str:
        """The configured leading-track kind (none | video | audio)."""
        return self.leading.kind

    def leading_file(self) -> str:
        """The configured leading-track file (empty when ``kind == none``)."""
        return self.leading.file


@dataclass(frozen=True)
class Playlist:
    """Top-level playlist: schema ``version`` + ``metadata`` + ordered ``members``."""

    version: str
    metadata: Metadata
    members: list[Member]

    def active_outputs(self) -> list[str]:
        """Delegate to :meth:`Metadata.active_outputs`."""
        return self.metadata.active_outputs()

    def active_mix_streams(self) -> list[str]:
        """Delegate to :meth:`Metadata.active_mix_streams`."""
        return self.metadata.active_mix_streams()

    def leading_kind(self) -> str:
        """Delegate to :meth:`Metadata.leading_kind`."""
        return self.metadata.leading_kind()

    def leading_file(self) -> str:
        """Delegate to :meth:`Metadata.leading_file`."""
        return self.metadata.leading_file()
