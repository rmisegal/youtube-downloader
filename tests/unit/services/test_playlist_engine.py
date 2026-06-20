"""Unit tests for :class:`PlaylistEngine` (PRD-mixer §4.1 + §4.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ytdl.services.mixer.playlist_engine import PlaylistEngine
from ytdl.shared.config import ConfigManager


def _config() -> ConfigManager:
    return ConfigManager(data={"version": "1.02"})


def _engine(**kwargs) -> PlaylistEngine:
    return PlaylistEngine(_config(), **kwargs)


def _make_tracks(tmp_path: Path) -> list[Path]:
    names = ["a.mp4", "b.mkv", "c.mp4", "notes.txt", "thumb.jpg"]
    for name in names:
        (tmp_path / name).write_text("x", encoding="utf-8")
    return sorted(tmp_path / n for n in ("a.mp4", "b.mkv", "c.mp4"))


def test_scan_indexes_only_supported_sorted(tmp_path: Path) -> None:
    _make_tracks(tmp_path)
    result = _engine().scan(tmp_path)
    assert [p.name for p in result] == ["a.mp4", "b.mkv", "c.mp4"]


def test_scan_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _engine().scan(tmp_path / "nope")


def test_scan_removable_drive_unmounted_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "drive", property(lambda self: "D:"))
    monkeypatch.setattr(Path, "exists", lambda self: False)
    with pytest.raises(FileNotFoundError, match="Drive not mounted"):
        _engine().scan("D:/media")


def test_select_random_applies_shuffle_without_mutating_input(tmp_path: Path) -> None:
    tracks = _make_tracks(tmp_path)
    original = list(tracks)
    result = _engine(shuffle_fn=list.reverse).select(tracks, "random")
    assert result == list(reversed(original))
    assert tracks == original  # input untouched


def test_select_manual_picks_requested_indices(tmp_path: Path) -> None:
    tracks = _make_tracks(tmp_path)
    engine = _engine(input_fn=lambda _prompt: "1,3")
    result = engine.select(tracks, "manual", tty=True)
    assert result == [tracks[0], tracks[2]]


def test_select_manual_non_tty_returns_all(tmp_path: Path) -> None:
    tracks = _make_tracks(tmp_path)
    result = _engine(input_fn=lambda _p: "1").select(tracks, "manual", tty=False)
    assert result == tracks


def test_select_manual_eof_returns_all(tmp_path: Path) -> None:
    def _raise(_prompt: str) -> str:
        raise EOFError

    tracks = _make_tracks(tmp_path)
    result = _engine(input_fn=_raise).select(tracks, "manual", tty=True)
    assert result == tracks


def test_select_manual_empty_reply_returns_all(tmp_path: Path) -> None:
    tracks = _make_tracks(tmp_path)
    result = _engine(input_fn=lambda _p: "  ").select(tracks, "manual", tty=True)
    assert result == tracks
