"""Unit tests for :class:`Sampler` (PRD-playlist §3 sampler, §4 play-for-sec)."""

from __future__ import annotations

import random
from pathlib import Path

from ytdl.services.mixer.sampler import Sampler
from ytdl.shared.config import ConfigManager


class _FakeEngine:
    """Stand-in for :class:`PlaylistEngine` that returns canned tracks."""

    def __init__(self, tracks: list[Path]) -> None:
        self._tracks = tracks

    def scan(self, _directory: Path | str) -> list[Path]:
        return list(self._tracks)


class _FakeFfmpeg:
    """No-op FFmpeg locator (the duration_fn is faked, so exe() is unused)."""

    def exe(self) -> str:
        return "ffmpeg"


def _config(**sample: object) -> ConfigManager:
    return ConfigManager(data={"version": "1.03", "sample": sample})


def _sampler(tracks: list[Path], *, seed: int = 0, duration: float = 100.0, **sample) -> Sampler:
    return Sampler(
        _config(**sample),
        playlist_engine=_FakeEngine(tracks),
        duration_fn=lambda _path, _exe: duration,
        rng=random.Random(seed),
        ffmpeg=_FakeFfmpeg(),
    )


def test_start_is_deterministic_within_mid_band() -> None:
    tracks = [Path("a.mp4")]
    first = _sampler(tracks, seed=1234).build_segments("dir")[0].start
    second = _sampler(tracks, seed=1234).build_segments("dir")[0].start
    assert first == second  # reproducible under a fixed seed
    assert 25.0 <= first <= 75.0  # band 0.25-0.75 * duration 100


def test_mid_band_bounds_come_from_config() -> None:
    tracks = [Path("a.mp4")]
    start = _sampler(tracks, seed=1234, mid_band_low=0.9, mid_band_high=0.95).build_segments(
        "dir"
    )[0].start
    assert 90.0 <= start <= 95.0


def test_play_seconds_default_from_config() -> None:
    tracks = [Path("a.mp4")]
    segments = _sampler(tracks, play_seconds=10).build_segments("dir")
    assert segments[0].play_seconds == 10


def test_play_for_sec_override() -> None:
    tracks = [Path("a.mp4"), Path("b.mkv")]
    segments = _sampler(tracks, play_seconds=10).build_segments("dir", play_for_sec=4)
    assert [s.play_seconds for s in segments] == [4, 4]


def test_one_segment_per_track_with_path_set() -> None:
    tracks = [Path("a.mp4"), Path("b.mkv"), Path("c.mp4")]
    segments = _sampler(tracks).build_segments("dir")
    assert [s.path for s in segments] == [str(t) for t in tracks]


def test_loop_attribute_reflects_config() -> None:
    assert _sampler([], loop=True).loop is True
    assert _sampler([], loop=False).loop is False
