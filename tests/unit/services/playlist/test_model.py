"""Unit tests for playlist model dataclasses + selection accessors (PRD §5.2/§5.4).

Constructs dataclasses directly — no YAML parsing or network here.
"""

from __future__ import annotations

import dataclasses

import pytest

from ytdl.constants import (
    EFFECT_FADE,
    LEADING_AUDIO,
    LEADING_NONE,
    OUTPUT_DISPLAY,
    OUTPUT_SAVE,
)
from ytdl.services.playlist.model import (
    Leading,
    Member,
    Metadata,
    MixToggles,
    Output,
    Playlist,
)


def test_member_defaults() -> None:
    m = Member(id=1, file="intro.mp4")
    assert m.id == 1
    assert m.file == "intro.mp4"
    assert m.start_time == 0.0
    assert m.play_time is None
    assert m.playback_speed == 1.0
    assert m.resolution == "max"
    assert m.subtitle is None
    assert m.effect == EFFECT_FADE == "fade"


def test_leading_defaults() -> None:
    lead = Leading()
    assert lead.kind == LEADING_NONE == "none"
    assert lead.file == ""


def test_mix_toggles_defaults() -> None:
    mix = MixToggles()
    assert mix.video is True
    assert mix.audio is True
    assert mix.subtitle is False


def test_output_defaults() -> None:
    out = Output()
    assert out.display is True
    assert out.save is False
    assert out.stream is False


def test_metadata_defaults() -> None:
    meta = Metadata()
    assert meta.source_folder == ""
    assert meta.target_folder == ""
    assert meta.output == Output()
    assert meta.mix == MixToggles()
    assert meta.leading == Leading()
    assert meta.loop is True


def test_member_is_frozen() -> None:
    m = Member(id=1, file="intro.mp4")
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.start_time = 5.0  # type: ignore[misc]


def test_active_outputs_returns_only_enabled() -> None:
    meta = Metadata(output=Output(display=True, save=True, stream=False))
    assert meta.active_outputs() == [OUTPUT_DISPLAY, OUTPUT_SAVE]


def test_active_outputs_empty_when_all_off() -> None:
    meta = Metadata(output=Output(display=False, save=False, stream=False))
    assert meta.active_outputs() == []


def test_active_mix_streams_excludes_disabled_toggle() -> None:
    meta = Metadata(mix=MixToggles(video=True, audio=True, subtitle=False))
    streams = meta.active_mix_streams()
    assert "subtitle" not in streams
    assert streams == ["video", "audio"]


def test_leading_kind_and_file() -> None:
    meta = Metadata(leading=Leading(kind=LEADING_AUDIO, file="master.mp3"))
    assert meta.leading_kind() == LEADING_AUDIO == "audio"
    assert meta.leading_file() == "master.mp3"


def test_playlist_delegates_accessors() -> None:
    meta = Metadata(
        output=Output(display=True, save=False, stream=True),
        mix=MixToggles(video=True, audio=False, subtitle=False),
        leading=Leading(kind=LEADING_AUDIO, file="m.wav"),
    )
    pl = Playlist(version="1.03", metadata=meta, members=[Member(id=1, file="a.mp4")])
    assert pl.active_outputs() == ["display", "stream"]
    assert pl.active_mix_streams() == ["video"]
    assert pl.leading_kind() == "audio"
    assert pl.leading_file() == "m.wav"
    assert pl.version == "1.03"
    assert pl.members[0].id == 1
