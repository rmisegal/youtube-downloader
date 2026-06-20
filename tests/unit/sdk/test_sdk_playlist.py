"""Unit tests for SDK playlist behaviour (probe + download params).

A mock :class:`YtDlpClient` stands in for the network: ``extract_info`` returns a
crafted info dict, ``download`` records its opts. No network, no files beyond the
temp output dir.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ytdl.sdk.sdk import YoutubeDownloaderSDK
from ytdl.shared.config import ConfigManager

_SAMPLE: dict = {
    "version": "1.00",
    "paths": {"output_dir": "./downloads"},
    "defaults": {"resolution": 720, "sub_lang": "en", "modes": ["video"]},
    "audio": {"codec": "mp3", "quality": "192"},
    "subtitles": {"format": "srt", "include_auto": True},
    "ffmpeg": {"location": "auto"},
}


@pytest.fixture
def mock_client() -> MagicMock:
    client = MagicMock(name="YtDlpClient")
    client.download.return_value = {"id": "abc"}
    return client


@pytest.fixture
def sdk(mock_client: MagicMock) -> YoutubeDownloaderSDK:
    return YoutubeDownloaderSDK(client=mock_client, config=ConfigManager(data=dict(_SAMPLE)))


def _dl_opts(mock_client: MagicMock) -> dict:
    return mock_client.download.call_args.args[1]


def test_probe_playlist_returns_count_and_entries(sdk, mock_client) -> None:
    mock_client.extract_info.return_value = {
        "_type": "playlist",
        "title": "My List",
        "playlist_count": 5,
        "entries": [{"id": "a", "title": "First"}, {"id": "b", "title": "Second"}],
    }
    info = sdk.probe_playlist("https://yt/playlist?list=Y")
    assert info["title"] == "My List"
    assert info["count"] == 5
    assert info["entries"] == [
        {"index": 1, "id": "a", "title": "First"},
        {"index": 2, "id": "b", "title": "Second"},
    ]


def test_probe_playlist_count_falls_back_to_len(sdk, mock_client) -> None:
    mock_client.extract_info.return_value = {
        "_type": "playlist",
        "title": "L",
        "entries": [{"id": "a"}],
    }
    info = sdk.probe_playlist("https://yt/playlist?list=Y")
    # No title on the entry -> falls back to id.
    assert info["count"] == 1
    assert info["entries"][0]["title"] == "a"


def test_probe_playlist_returns_none_for_single_video(sdk, mock_client) -> None:
    mock_client.extract_info.return_value = {"_type": "video", "id": "x", "title": "T"}
    assert sdk.probe_playlist("https://yt/watch?v=x") is None


def test_download_no_playlist_sets_noplaylist(sdk, mock_client, tmp_path) -> None:
    sdk.download("u", output_dir=str(tmp_path / "o"), no_playlist=True)
    opts = _dl_opts(mock_client)
    assert opts["noplaylist"] is True
    assert "playlist_items" not in opts


def test_download_playlist_items_sets_key(sdk, mock_client, tmp_path) -> None:
    sdk.download("u", output_dir=str(tmp_path / "o"), playlist_items="1,3")
    opts = _dl_opts(mock_client)
    assert opts["playlist_items"] == "1,3"
    assert "noplaylist" not in opts


def test_download_neither_flag_absent(sdk, mock_client, tmp_path) -> None:
    sdk.download("u", output_dir=str(tmp_path / "o"))
    opts = _dl_opts(mock_client)
    assert "noplaylist" not in opts
    assert "playlist_items" not in opts
