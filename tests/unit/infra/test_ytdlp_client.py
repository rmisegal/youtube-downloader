"""Unit tests for :class:`ytdl.infra.ytdlp_client.YtDlpClient`.

No network: ``yt_dlp.YoutubeDL`` is patched with a ``MagicMock`` and a fake
gatekeeper whose ``execute`` simply calls ``func(*a, **k)`` is used so we can
assert routing (every call goes through the gatekeeper).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ytdl.infra.ytdlp_client import YtDlpClient
from ytdl.shared.errors import (
    InvalidUrlError,
    NetworkError,
    RateLimitExceededError,
    UnsupportedRequestError,
)

URL = "https://youtu.be/dQw4w9WgXcQ"
OPTS: dict[str, Any] = {"format": "bv*+ba/b", "merge_output_format": "mp4"}
INFO: dict[str, Any] = {"id": "dQw4w9WgXcQ", "title": "Sample"}


class FakeGatekeeper:
    """Pass-through gatekeeper recording that ``execute`` was used."""

    def __init__(self) -> None:
        self.execute = MagicMock(side_effect=lambda func, *a, **k: func(*a, **k))


def test_extract_info_routes_through_gatekeeper_with_download_false() -> None:
    """``extract_info`` goes via the gatekeeper and calls download=False."""
    gate = FakeGatekeeper()
    client = YtDlpClient(gate)
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = INFO
        result = client.extract_info(URL, OPTS)

    gate.execute.assert_called_once()
    mock_ydl.assert_called_once_with(OPTS)
    mock_ydl.return_value.extract_info.assert_called_once_with(URL, download=False)
    assert result == INFO


def test_download_routes_through_gatekeeper_with_download_true() -> None:
    """``download`` goes via the gatekeeper and calls download=True."""
    gate = FakeGatekeeper()
    client = YtDlpClient(gate)
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = INFO
        result = client.download(URL, OPTS)

    gate.execute.assert_called_once()
    mock_ydl.assert_called_once_with(OPTS)
    mock_ydl.return_value.extract_info.assert_called_once_with(URL, download=True)
    assert result == INFO


def test_extract_info_returns_ytdlp_result() -> None:
    """The value returned is exactly what yt-dlp returned."""
    sentinel = {"unique": object()}
    client = YtDlpClient(FakeGatekeeper())
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = sentinel
        assert client.extract_info(URL, OPTS) is sentinel


def test_download_returns_ytdlp_result() -> None:
    """``download`` returns exactly what yt-dlp returned."""
    sentinel = {"unique": object()}
    client = YtDlpClient(FakeGatekeeper())
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = sentinel
        assert client.download(URL, OPTS) is sentinel


def test_opts_passed_through_untouched() -> None:
    """The exact opts dict is handed to ``YoutubeDL`` (no business logic)."""
    gate = FakeGatekeeper()
    client = YtDlpClient(gate)
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.return_value = INFO
        client.extract_info(URL, OPTS)
    passed_opts = mock_ydl.call_args.args[0]
    assert passed_opts is OPTS


def test_unsupported_error_translated() -> None:
    """yt-dlp ``UnsupportedError`` becomes :class:`UnsupportedRequestError`."""
    from yt_dlp.utils import UnsupportedError

    client = YtDlpClient(FakeGatekeeper())
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.side_effect = UnsupportedError(URL)
        with pytest.raises(UnsupportedRequestError):
            client.download(URL, OPTS)


def test_invalid_url_download_error_translated() -> None:
    """A DownloadError whose message indicates a bad URL → InvalidUrlError."""
    from yt_dlp.utils import DownloadError

    client = YtDlpClient(FakeGatekeeper())
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.side_effect = DownloadError(
            "ERROR: 'x' is not a valid URL"
        )
        with pytest.raises(InvalidUrlError):
            client.download(URL, OPTS)


def test_generic_download_error_translated_to_network() -> None:
    """A generic DownloadError → NetworkError."""
    from yt_dlp.utils import DownloadError

    client = YtDlpClient(FakeGatekeeper())
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.side_effect = DownloadError(
            "ERROR: unable to download: connection reset by peer"
        )
        with pytest.raises(NetworkError):
            client.download(URL, OPTS)


def test_rate_limit_429_download_error_translated() -> None:
    """A DownloadError reporting HTTP 429 → RateLimitExceededError."""
    from yt_dlp.utils import DownloadError

    client = YtDlpClient(FakeGatekeeper())
    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.side_effect = DownloadError(
            "HTTP Error 429: Too Many Requests"
        )
        with pytest.raises(RateLimitExceededError):
            client.download(URL, OPTS)

    with patch("yt_dlp.YoutubeDL") as mock_ydl:
        mock_ydl.return_value.extract_info.side_effect = DownloadError(
            "HTTP Error 429: Too Many Requests"
        )
        with pytest.raises(RateLimitExceededError):
            client.extract_info(URL, OPTS)
