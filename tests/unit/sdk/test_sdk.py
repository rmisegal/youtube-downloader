"""Unit tests for :class:`YoutubeDownloaderSDK` (no network; mock client).

A mock :class:`YtDlpClient` captures every ``download`` call so we can assert the
merged opts and the fetch-once guarantee. A real :class:`ConfigManager` (sample
data) supplies defaults; ``tmp_path`` provides the output dir.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ytdl.constants import PP_CONVERT_SUBS, PP_EXTRACT_AUDIO
from ytdl.sdk.sdk import YoutubeDownloaderSDK
from ytdl.shared.config import ConfigManager

_SAMPLE: dict = {
    "version": "1.00",
    "paths": {"output_dir": "./downloads"},
    "defaults": {"resolution": 720, "sub_lang": "fr", "modes": ["video"]},
    "audio": {"codec": "mp3", "quality": "192"},
    "subtitles": {"format": "srt", "include_auto": True},
    "ffmpeg": {"location": "auto"},
}


@pytest.fixture
def mock_client() -> MagicMock:
    """A mock YtDlpClient whose ``download`` records its args."""
    client = MagicMock(name="YtDlpClient")
    client.download.return_value = {"id": "abc"}
    return client


@pytest.fixture
def sdk(mock_client: MagicMock) -> YoutubeDownloaderSDK:
    """SDK wired with the mock client and sample config."""
    config = ConfigManager(data=dict(_SAMPLE))
    return YoutubeDownloaderSDK(client=mock_client, config=config)


def _opts(mock_client: MagicMock) -> dict:
    """Return the opts dict passed to the single download call."""
    return mock_client.download.call_args.args[1]


def _pp_keys(opts: dict) -> list[str]:
    return [pp["key"] for pp in opts.get("postprocessors", [])]


def test_no_flags_defaults_to_video(sdk, mock_client, tmp_path):
    result = sdk.download("u", output_dir=str(tmp_path / "out"))
    opts = _opts(mock_client)
    assert result["modes"] == ["video"]
    assert "format" in opts
    assert opts["merge_output_format"] == "mp4"
    assert PP_EXTRACT_AUDIO not in _pp_keys(opts)


def test_audio_only(sdk, mock_client, tmp_path):
    sdk.download("u", audio=True, output_dir=str(tmp_path / "out"))
    opts = _opts(mock_client)
    assert PP_EXTRACT_AUDIO in _pp_keys(opts)
    assert "format" not in opts


def test_subs_only(sdk, mock_client, tmp_path):
    sdk.download("u", subs=True, output_dir=str(tmp_path / "out"))
    opts = _opts(mock_client)
    assert opts["writesubtitles"] is True
    assert PP_CONVERT_SUBS in _pp_keys(opts)


def test_combined_union_and_keepvideo(sdk, mock_client, tmp_path):
    sdk.download(
        "u", video=True, audio=True, subs=True, output_dir=str(tmp_path / "out")
    )
    assert mock_client.download.call_count == 1
    opts = _opts(mock_client)
    keys = _pp_keys(opts)
    assert PP_EXTRACT_AUDIO in keys
    assert PP_CONVERT_SUBS in keys
    assert opts["keepvideo"] is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"audio": True},
        {"subs": True},
        {"video": True, "audio": True},
        {"video": True, "audio": True, "subs": True},
    ],
)
def test_download_called_exactly_once(sdk, mock_client, tmp_path, kwargs):
    sdk.download("u", output_dir=str(tmp_path / "out"), **kwargs)
    assert mock_client.download.call_count == 1


def test_output_dir_created_when_missing(sdk, tmp_path):
    target = tmp_path / "nested" / "downloads"
    assert not target.exists()
    sdk.download("u", output_dir=str(target))
    assert target.is_dir()


def test_defaults_pulled_from_config(sdk, mock_client, tmp_path):
    # No output_dir/resolution/sub_lang passed -> taken from sample config.
    sdk.download("u", subs=True)
    opts = _opts(mock_client)
    # sub_lang default "fr" from config feeds the subtitle langs.
    assert opts["subtitleslangs"] == ["fr"]
    # output_dir default "./downloads" feeds outtmpl.
    assert "downloads" in opts["outtmpl"]
    assert Path("./downloads").is_dir()


def test_video_resolution_default_from_config(sdk, mock_client, tmp_path):
    sdk.download("u", video=True, output_dir=str(tmp_path / "out"))
    opts = _opts(mock_client)
    # resolution default 720 from config -> capped format selector.
    assert "720" in opts["format"]


def test_version_returns_code_version():
    from ytdl.shared.version import __version__

    assert YoutubeDownloaderSDK.version() == __version__


def test_convenience_methods_delegate(sdk, mock_client, tmp_path):
    out = str(tmp_path / "out")
    assert sdk.download_audio("u", output_dir=out)["modes"] == ["audio"]
    assert sdk.download_subtitles("u", output_dir=out)["modes"] == ["subs"]
    assert sdk.download_video("u", output_dir=out)["modes"] == ["video"]


def test_build_client_wires_real_stack_without_network():
    """No injected client -> _build_client assembles the gatekeeper stack.

    Construction alone touches no network (no extract/download is called), so
    this safely covers the rate-limit/queue/gatekeeper wiring path.
    """
    from ytdl.infra.ytdlp_client import YtDlpClient

    config = ConfigManager(data=dict(_SAMPLE))
    rate_config = ConfigManager(
        data={
            "version": "1.00",
            "rate_limits": {
                "services": {"youtube": {"requests_per_minute": 20, "max_retries": 3}},
                "queue": {"max_depth": 100, "overflow_strategy": "reject_oldest"},
            },
        }
    )
    sdk = YoutubeDownloaderSDK(config=config, rate_config=rate_config)
    assert isinstance(sdk._client, YtDlpClient)


def test_empty_name_uses_title_template(sdk, mock_client, tmp_path):
    """An empty/None name falls back to the %(title)s output template."""
    sdk.download("u", name="", output_dir=str(tmp_path / "out"))
    opts = _opts(mock_client)
    assert "%(title)s" in opts["outtmpl"]
