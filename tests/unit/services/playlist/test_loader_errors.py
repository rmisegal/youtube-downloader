"""Branch-coverage tests for the playlist loader's validation/error paths.

Targets the residual gaps in ``loader.py``: unreadable file (``_read`` OSError),
missing ``version`` key, non-list ``members``, non-mapping member, member missing
``id``/``file``, and the ``_subset`` dict-comprehension path (metadata sub-blocks).
All boundaries stay local: YAML lives in ``tmp_path``; the OSError is injected via
monkeypatch. No network, render, or playback.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ytdl.services.playlist.loader import load_playlist
from ytdl.shared.errors import PlaylistError


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "playlist.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_read_oserror_wrapped_as_playlist_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, 'version: "1.03"\nmembers: []\n')

    def _boom(*_a: object, **_k: object) -> str:
        raise OSError("disk gone")

    monkeypatch.setattr(Path, "read_text", _boom)
    with pytest.raises(PlaylistError, match="Cannot read playlist file"):
        load_playlist(path)


def test_missing_version_key_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, "metadata: {}\nmembers: []\n")
    with pytest.raises(PlaylistError, match="missing required key: 'version'"):
        load_playlist(path)


def test_members_not_a_list_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, 'version: "1.03"\nmembers: 42\n')
    with pytest.raises(PlaylistError, match="'members' must be a list"):
        load_playlist(path)


def test_member_not_a_mapping_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, 'version: "1.03"\nmembers:\n  - "just a string"\n')
    with pytest.raises(PlaylistError, match="member must be a mapping"):
        load_playlist(path)


def test_member_missing_id_or_file_raises(tmp_path: Path) -> None:
    path = _write(tmp_path, 'version: "1.03"\nmembers:\n  - id: 1\n')
    with pytest.raises(PlaylistError, match="missing required 'id'/'file'"):
        load_playlist(path)


def test_metadata_subset_keeps_only_known_fields(tmp_path: Path) -> None:
    # Exercises ``_subset`` with real dicts (output/mix/leading) carrying an
    # unknown key, which must be silently dropped (not raised).
    yaml_text = (
        'version: "1.03"\n'
        "metadata:\n"
        '  source_folder: "src"\n'
        '  target_folder: "tgt"\n'
        "  loop: false\n"
        "  output:\n"
        '    bogus_key: "ignored"\n'
        "  mix:\n"
        '    bogus_key: "ignored"\n'
        "  leading:\n"
        '    bogus_key: "ignored"\n'
        "members: []\n"
    )
    path = _write(tmp_path, yaml_text)

    playlist = load_playlist(path)

    assert playlist.metadata.source_folder == "src"
    assert playlist.metadata.target_folder == "tgt"
    assert playlist.metadata.loop is False
    assert not hasattr(playlist.metadata.output, "bogus_key")
