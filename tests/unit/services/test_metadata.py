"""Unit tests for :class:`ytdl.services.metadata.MetadataService`.

No network: a ``MagicMock`` stands in for :class:`YtDlpClient`. We assert that
the service delegates to ``extract_info`` (never ``download``), passes opts
through, and extracts/falls-back the title correctly.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ytdl.services.metadata import MetadataService

URL = "https://youtu.be/abc123"


@pytest.fixture
def client() -> MagicMock:
    """A fake YtDlpClient whose ``extract_info`` returns a sample info dict."""
    fake = MagicMock(name="YtDlpClient")
    fake.extract_info.return_value = {"id": "abc123", "title": "Sample Video"}
    return fake


@pytest.fixture
def service(client: MagicMock) -> MetadataService:
    """A MetadataService wired to the fake client."""
    return MetadataService(client)


def test_info_returns_client_result(
    service: MetadataService, client: MagicMock
) -> None:
    """``info`` returns exactly what ``extract_info`` produced."""
    result = service.info(URL)
    assert result == {"id": "abc123", "title": "Sample Video"}
    assert result is client.extract_info.return_value


def test_info_passes_opts_through(
    service: MetadataService, client: MagicMock
) -> None:
    """``info`` forwards the URL and opts dict to ``extract_info``."""
    opts: dict[str, Any] = {"quiet": True}
    service.info(URL, opts)
    client.extract_info.assert_called_once_with(URL, opts)


def test_info_defaults_opts_to_empty_dict(
    service: MetadataService, client: MagicMock
) -> None:
    """``info`` substitutes ``{}`` when opts is omitted/None."""
    service.info(URL)
    client.extract_info.assert_called_once_with(URL, {})


def test_info_never_downloads(
    service: MetadataService, client: MagicMock
) -> None:
    """``info`` resolves metadata only — it never calls ``download``."""
    service.info(URL)
    client.download.assert_not_called()


def test_title_extracts_title_field(service: MetadataService) -> None:
    """``title`` returns the ``title`` field from the resolved info dict."""
    assert service.title(URL) == "Sample Video"


def test_title_forwards_opts(
    service: MetadataService, client: MagicMock
) -> None:
    """``title`` forwards opts to the underlying ``extract_info`` call."""
    opts = {"quiet": True}
    service.title(URL, opts)
    client.extract_info.assert_called_once_with(URL, opts)


def test_title_falls_back_to_id_when_title_missing(client: MagicMock) -> None:
    """Missing ``title`` falls back to the video ``id``."""
    client.extract_info.return_value = {"id": "vid42"}
    assert MetadataService(client).title(URL) == "vid42"


def test_title_falls_back_to_id_when_title_empty(client: MagicMock) -> None:
    """Empty/falsy ``title`` falls back to the video ``id``."""
    client.extract_info.return_value = {"id": "vid42", "title": ""}
    assert MetadataService(client).title(URL) == "vid42"


def test_title_empty_string_when_title_and_id_absent(client: MagicMock) -> None:
    """No ``title`` and no ``id`` yields a safe empty string."""
    client.extract_info.return_value = {}
    assert MetadataService(client).title(URL) == ""
