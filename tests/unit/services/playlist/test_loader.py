"""Unit tests for the YAML playlist loader (PRD-playlist §5.3 + R55/R56).

All boundaries are mocked: YAML lives in ``tmp_path``, member files are real
``tmp_path`` files, the removable-drive guard is patched via monkeypatch, and
the URL downloader is a fake. No network, render, or playback here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ytdl.services.mixer.segment import MixSegment
from ytdl.services.playlist import loader_build
from ytdl.services.playlist.loader import (
    SUPPORTED_PLAYLIST_VERSIONS,
    build_segments,
    load_playlist,
)
from ytdl.services.playlist.model import Playlist
from ytdl.shared.errors import PlaylistError


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "playlist.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _make_members(tmp_path: Path, *names: str) -> None:
    for name in names:
        (tmp_path / name).write_text("data", encoding="utf-8")


class FakeDownloader:
    """Records ``download`` calls and returns a canned local path."""

    def __init__(self, result: str) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def download(self, url: str, *, output_dir: str) -> str:
        self.calls.append((url, output_dir))
        return self.result


def _valid_yaml(folder: str) -> str:
    return f"""
version: "1.03"
metadata:
  source_folder: "{folder}"
  target_folder: "{folder}"
members:
  - id: 2
    file: "second.mp4"
    start_time: 5.0
    play_time: 8.0
    playback_speed: 1.25
    resolution: "1280x720"
    subtitle: "second.srt"
    effect: "fade"
  - id: 1
    file: "first.mp4"
"""


def test_valid_yaml_orders_members_by_id(tmp_path: Path) -> None:
    _make_members(tmp_path, "first.mp4", "second.mp4")
    path = _write(tmp_path, _valid_yaml(tmp_path.as_posix()))

    playlist = load_playlist(path)

    assert isinstance(playlist, Playlist)
    assert playlist.version == "1.03"
    assert [m.id for m in playlist.members] == [1, 2]


def test_build_segments_maps_all_fields(tmp_path: Path) -> None:
    _make_members(tmp_path, "first.mp4", "second.mp4")
    path = _write(tmp_path, _valid_yaml(tmp_path.as_posix()))

    segments = build_segments(load_playlist(path))

    assert [Path(s.path).name for s in segments] == ["first.mp4", "second.mp4"]
    second = segments[1]
    assert isinstance(second, MixSegment)
    assert second.start == 5.0
    assert second.play_seconds == 8.0
    assert second.speed == 1.25
    assert second.resolution == "1280x720"
    assert second.subtitle == "second.srt"
    assert second.effect == "fade"


def test_member_defaults_flow_into_segment(tmp_path: Path) -> None:
    _make_members(tmp_path, "first.mp4", "second.mp4")
    path = _write(tmp_path, _valid_yaml(tmp_path.as_posix()))

    first = build_segments(load_playlist(path))[0]

    assert first.start == 0.0
    assert first.play_seconds is None
    assert first.speed == 1.0
    assert first.resolution == "max"
    assert first.subtitle is None


def test_no_separator_file_resolved_under_source_folder(tmp_path: Path) -> None:
    _make_members(tmp_path, "first.mp4", "second.mp4")
    path = _write(tmp_path, _valid_yaml(tmp_path.as_posix()))

    segments = build_segments(load_playlist(path))

    assert Path(segments[0].path).parent == tmp_path


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, "version: '1.03'\nmembers: [unclosed")
    with pytest.raises(PlaylistError):
        load_playlist(path)


def test_non_dict_yaml_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, "- just\n- a\n- list")
    with pytest.raises(PlaylistError):
        load_playlist(path)


def test_unsupported_version_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, 'version: "9.99"\nmembers: []')
    with pytest.raises(PlaylistError):
        load_playlist(path)
    assert "9.99" not in SUPPORTED_PLAYLIST_VERSIONS


def test_safe_load_does_not_execute_python_tags(tmp_path: Path) -> None:
    # A `!!python/object` tag must NOT be constructed (yaml.safe_load, Rule 13).
    path = _write(
        tmp_path,
        'version: "1.03"\nmembers:\n  - !!python/object/apply:os.system ["echo hi"]\n',
    )
    with pytest.raises(PlaylistError):
        load_playlist(path)


def test_missing_member_file_raises(tmp_path: Path) -> None:
    # Only first.mp4 exists; second.mp4 is missing.
    _make_members(tmp_path, "first.mp4")
    path = _write(tmp_path, _valid_yaml(tmp_path.as_posix()))
    with pytest.raises(PlaylistError, match="not found"):
        build_segments(load_playlist(path))


def test_removable_drive_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    yaml_text = (
        'version: "1.03"\n'
        "metadata:\n"
        '  source_folder: ""\n'
        "members:\n"
        '  - id: 1\n'
        '    file: "D:/videos/clip.mp4"\n'
    )
    path = _write(tmp_path, yaml_text)

    real_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if str(self) in ("D:/", "D:\\"):
            return False
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    with pytest.raises(PlaylistError, match="not mounted"):
        build_segments(load_playlist(path))


def test_url_member_uses_downloader(tmp_path: Path) -> None:
    local = tmp_path / "downloaded.mp4"
    local.write_text("data", encoding="utf-8")
    yaml_text = (
        'version: "1.03"\n'
        "metadata:\n"
        f'  target_folder: "{tmp_path.as_posix()}"\n'
        "members:\n"
        '  - id: 1\n'
        '    file: "https://youtu.be/abc"\n'
    )
    path = _write(tmp_path, yaml_text)
    fake = FakeDownloader(result=str(local))

    segments = build_segments(load_playlist(path), downloader=fake)

    assert fake.calls == [("https://youtu.be/abc", tmp_path.as_posix())]
    assert segments[0].path == str(local)


def test_url_member_without_downloader_raises(tmp_path: Path) -> None:
    yaml_text = (
        'version: "1.03"\nmembers:\n  - id: 1\n    file: "https://youtu.be/abc"\n'
    )
    path = _write(tmp_path, yaml_text)
    with pytest.raises(PlaylistError):
        build_segments(load_playlist(path))


def test_guard_removable_passes_for_local_c_drive(tmp_path: Path) -> None:
    # Sanity: the guard helper does not flag a normal (non-D:/H:) path.
    loader_build._guard_removable(tmp_path / "x.mp4")
