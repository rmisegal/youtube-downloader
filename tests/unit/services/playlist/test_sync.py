"""Unit tests for the music-sync pre-pass (placement + profile/target wiring)."""

from __future__ import annotations

from unittest.mock import MagicMock

from ytdl.services.mixer.segment import MixSegment
from ytdl.services.playlist.loader import _build_metadata
from ytdl.services.playlist.model import Leading, Metadata, Playlist, Sync
from ytdl.services.playlist.sync import (
    apply_sync,
    build_overlay,
    place_on_cuts,
    sync_segments,
)
from ytdl.services.playlist.track_model import TrackElement, Tracks


def _segs(n: int = 2) -> list[MixSegment]:
    return [MixSegment(path=f"{i}.jpg", kind="image", transition="random") for i in range(n)]


def _cut(t, transition="pulse", section="Verse"):
    return {"timestamp_sec": t, "transition": transition, "section": section,
            "hold_beats": 4, "unique": False}


def test_place_assigns_slots_and_uses_planner_transition() -> None:
    cuts = [_cut(0.0, "pulse", "Chorus"), _cut(2.0, "fade", "Verse")]
    out = place_on_cuts(_segs(2), cuts, total=4.0, bpm=128.0)
    assert out[0].at == 0.0 and out[0].until == 2.0 and out[0].play_seconds == 2.0
    assert out[0].transition == "pulse" and out[0].bpm == 128.0      # planner-chosen effect
    assert out[1].at == 2.0 and out[1].until == 4.0 and out[1].transition == "fade"


def test_members_cycle_across_cuts() -> None:
    cuts = [_cut(float(i)) for i in range(3)]
    out = place_on_cuts(_segs(2), cuts, total=3.0, bpm=120.0)
    assert [o.path for o in out] == ["0.jpg", "1.jpg", "0.jpg"]


def test_sync_segments_drives_off_profile_and_analyzer() -> None:
    analyzer = MagicMock()
    analyzer.analyze.return_value = {
        "metadata": {"duration_seconds": 8.0, "global_bpm": 120.0},
        "cut_points": {"beats": [{"timestamp_sec": float(t)} for t in range(8)],
                       "sections": [{"start_sec": 0.0, "end_sec": 8.0, "label": "Verse"}]},
    }
    cfg = MagicMock()
    cfg.get.side_effect = lambda k, d=None: d
    out = sync_segments(_segs(2), "song.mp3", cfg, mode="auto", target="dj_party", analyzer=analyzer)
    # dj_party holds 2 beats in a Verse -> 4 slots over 8 beats; transitions from its pool.
    assert len(out) == 4 and out[0].at == 0.0
    assert all(o.transition in ("pulse", "flash", "shake", "bounce", "zoomin") for o in out)


def test_apply_sync_noop_when_disabled() -> None:
    pl = Playlist("1.05", Metadata(sync=Sync(enabled=False)), [])
    segs = _segs(2)
    assert apply_sync(pl, segs, MagicMock()) is segs


def test_apply_sync_requires_audio_leading() -> None:
    pl = Playlist("1.05", Metadata(sync=Sync(enabled=True), leading=Leading(kind="none")), [])
    segs = _segs(2)
    assert apply_sync(pl, segs, MagicMock()) is segs


def test_loader_parses_sync_target_and_mode() -> None:
    meta = _build_metadata({"sync": {"enabled": True, "mode": "auto", "target": "lecture"}})
    assert meta.sync_enabled() is True
    assert meta.sync_mode() == "auto" and meta.sync_target() == "lecture"
    assert _build_metadata({}).sync_target() == ""


def test_loader_parses_sync_crossfade() -> None:
    meta = _build_metadata({"sync": {"enabled": True, "crossfade": 0.5}})
    assert meta.sync_crossfade() == 0.5
    assert _build_metadata({}).sync_crossfade() == 0.0  # default = clean cuts


def test_build_overlay_none_without_tracks() -> None:
    pl = Playlist("1.05", Metadata(leading=Leading(kind="audio", file="s.mp3")), [])
    assert build_overlay(pl, MagicMock(), analyzer=MagicMock()) is None


def test_build_overlay_bundles_elements_and_beat_grid() -> None:
    analyzer = MagicMock()
    analyzer.analyze.return_value = {
        "metadata": {"global_bpm": 120.0, "duration_seconds": 10.0},
        "cut_points": {"beats": [{"timestamp_sec": 1.0}, {"timestamp_sec": 2.0}]},
    }
    pl = Playlist("1.05", Metadata(
        leading=Leading(kind="audio", file="s.mp3"),
        tracks=Tracks(titles=(TrackElement(text="HI", at_beat=4),))), [])
    payload = build_overlay(pl, MagicMock(), analyzer=analyzer)
    assert payload["bpm"] == 120.0 and payload["total"] == 10.0
    assert payload["beats"] == [1.0, 2.0] and len(payload["elements"]) == 1
