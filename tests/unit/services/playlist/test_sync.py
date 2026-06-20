"""Unit tests for the music-sync pre-pass (placement + transition fitting)."""

from __future__ import annotations

from unittest.mock import MagicMock

from ytdl.services.mixer.segment import MixSegment
from ytdl.services.playlist.loader import _build_metadata
from ytdl.services.playlist.model import Leading, Metadata, Playlist, Sync
from ytdl.services.playlist.sync import apply_sync, place_on_cuts, sync_segments


def _segs(n: int = 2) -> list[MixSegment]:
    return [MixSegment(path=f"{i}.jpg", kind="image", transition="random") for i in range(n)]


def test_place_assigns_slots_and_fits_transition() -> None:
    plan = [
        {"timestamp_sec": 0.0, "tier": "beat", "section": "Chorus"},
        {"timestamp_sec": 2.0, "tier": "bar", "section": "Verse"},
    ]
    out = place_on_cuts(_segs(2), plan, total=4.0, bpm=128.0,
                        tier_map={"beat": "pulse", "bar": "fade"}, section_map={"Chorus": "pulse"})
    assert out[0].at == 0.0 and out[0].until == 2.0 and out[0].play_seconds == 2.0
    assert out[0].transition == "pulse" and out[0].bpm == 128.0
    assert out[1].at == 2.0 and out[1].until == 4.0 and out[1].transition == "fade"


def test_section_map_overrides_tier_map() -> None:
    plan = [{"timestamp_sec": 0.0, "tier": "beat", "section": "Build-up"}]
    out = place_on_cuts(_segs(1), plan, total=2.0, bpm=120.0,
                        tier_map={"beat": "pulse"}, section_map={"Build-up": "shake"})
    assert out[0].transition == "shake"  # shake fits a build-up


def test_members_cycle_across_cuts() -> None:
    plan = [{"timestamp_sec": float(i), "tier": "beat", "section": "x"} for i in range(3)]
    out = place_on_cuts(_segs(2), plan, total=3.0, bpm=120.0)
    assert [o.path for o in out] == ["0.jpg", "1.jpg", "0.jpg"]


def test_sync_segments_drives_off_analyzer() -> None:
    analyzer = MagicMock()
    analyzer.analyze.return_value = {
        "metadata": {"duration_seconds": 4.0, "global_bpm": 120.0},
        "cut_points": {"beats": [{"timestamp_sec": 0.0}, {"timestamp_sec": 2.0}],
                       "bars": [], "phrases": [], "sections": []},
    }
    cfg = MagicMock()
    cfg.get.side_effect = lambda k, d=None: {"analysis.tier_transitions": {"beat": "pulse"}}.get(k, d)
    out = sync_segments(_segs(2), "song.mp3", cfg, mode="beat", analyzer=analyzer)
    assert len(out) == 2 and out[0].at == 0.0 and out[0].transition == "pulse"


def test_apply_sync_noop_when_disabled() -> None:
    pl = Playlist("1.05", Metadata(sync=Sync(enabled=False)), [])
    segs = _segs(2)
    assert apply_sync(pl, segs, MagicMock()) is segs


def test_apply_sync_requires_audio_leading() -> None:
    pl = Playlist("1.05", Metadata(sync=Sync(enabled=True), leading=Leading(kind="none")), [])
    segs = _segs(2)
    assert apply_sync(pl, segs, MagicMock()) is segs


def test_loader_parses_sync_block() -> None:
    meta = _build_metadata({"sync": {"enabled": True, "mode": "bar"}})
    assert meta.sync_enabled() is True and meta.sync_mode() == "bar"
    assert _build_metadata({}).sync_enabled() is False
