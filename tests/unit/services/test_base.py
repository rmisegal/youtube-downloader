"""Unit tests for :class:`ytdl.services.base.BaseDownloader`.

``FfmpegLocator.exe_dir`` is patched to a fake dir and env vars are driven via
``monkeypatch`` — no real FFmpeg, no network.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from ytdl.constants import DEFAULT_NAME_TEMPLATE, ENV_COOKIES_FILE, ENV_PROXY
from ytdl.services.base import BaseDownloader
from ytdl.shared.config import ConfigManager

FAKE_DIR = os.path.join(os.sep, "fake", "bin")
OUT_DIR = os.path.join(os.sep, "out")


@pytest.fixture
def downloader(monkeypatch: pytest.MonkeyPatch) -> BaseDownloader:
    """A BaseDownloader with a clean env and patched ffmpeg dir."""
    monkeypatch.delenv(ENV_PROXY, raising=False)
    monkeypatch.delenv(ENV_COOKIES_FILE, raising=False)
    return BaseDownloader(ConfigManager(data={"version": "1.00"}))


def _build(dl: BaseDownloader, output_dir: str, name: str | None) -> dict[str, Any]:
    with patch("ytdl.infra.ffmpeg.FfmpegLocator.exe_dir", return_value=FAKE_DIR):
        return dl.build_base_opts(output_dir, name)


def test_outtmpl_from_output_dir_and_name(downloader: BaseDownloader) -> None:
    """``outtmpl`` joins output_dir + name + the literal ``%(ext)s`` tail."""
    opts = _build(downloader, OUT_DIR, "sample")
    assert opts["outtmpl"] == str(Path(OUT_DIR) / "sample.%(ext)s")


def test_outtmpl_falls_back_to_title_template(downloader: BaseDownloader) -> None:
    """Falsy name falls back to the ``%(title)s`` template."""
    for empty in ("", None):
        opts = _build(downloader, OUT_DIR, empty)
        assert opts["outtmpl"] == str(Path(OUT_DIR) / DEFAULT_NAME_TEMPLATE)


def test_ffmpeg_location_wired_from_locator(downloader: BaseDownloader) -> None:
    """``ffmpeg_location`` comes from the locator's ``exe_dir``."""
    opts = _build(downloader, OUT_DIR, "x")
    assert opts["ffmpeg_location"] == FAKE_DIR


def test_proxy_present_when_env_set(
    downloader: BaseDownloader, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``proxy`` equals ``YTDL_PROXY`` when the env var is set."""
    monkeypatch.setenv(ENV_PROXY, "http://proxy:8080")
    opts = _build(downloader, OUT_DIR, "x")
    assert opts["proxy"] == "http://proxy:8080"


def test_proxy_absent_when_env_unset(
    downloader: BaseDownloader, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``proxy`` key is absent when ``YTDL_PROXY`` is unset."""
    monkeypatch.delenv(ENV_PROXY, raising=False)
    opts = _build(downloader, OUT_DIR, "x")
    assert "proxy" not in opts


def test_proxy_absent_when_env_empty(
    downloader: BaseDownloader, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``proxy`` key is absent when ``YTDL_PROXY`` is an empty string."""
    monkeypatch.setenv(ENV_PROXY, "")
    opts = _build(downloader, OUT_DIR, "x")
    assert "proxy" not in opts


def test_cookiefile_present_when_env_set(
    downloader: BaseDownloader, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``cookiefile`` equals ``YTDL_COOKIES_FILE`` when set."""
    monkeypatch.setenv(ENV_COOKIES_FILE, "/secrets/cookies.txt")
    opts = _build(downloader, OUT_DIR, "x")
    assert opts["cookiefile"] == "/secrets/cookies.txt"


def test_cookiefile_absent_when_unset_or_empty(
    downloader: BaseDownloader, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``cookiefile`` key is absent when the env var is unset or empty."""
    monkeypatch.delenv(ENV_COOKIES_FILE, raising=False)
    assert "cookiefile" not in _build(downloader, OUT_DIR, "x")
    monkeypatch.setenv(ENV_COOKIES_FILE, "")
    assert "cookiefile" not in _build(downloader, OUT_DIR, "x")


def test_base_mode_opts_is_empty(downloader: BaseDownloader) -> None:
    """The base ``_mode_opts`` hook contributes nothing."""
    assert downloader._mode_opts() == {}


def test_build_opts_merges_base_and_mode_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``build_opts`` merges base opts with a subclass ``_mode_opts``."""
    monkeypatch.delenv(ENV_PROXY, raising=False)
    monkeypatch.delenv(ENV_COOKIES_FILE, raising=False)

    class _Stub(BaseDownloader):
        def _mode_opts(self, **kwargs: Any) -> dict[str, Any]:
            return {"format": "bv*+ba/b", "merge_output_format": "mp4"}

    dl = _Stub(ConfigManager(data={"version": "1.00"}))
    with patch("ytdl.infra.ffmpeg.FfmpegLocator.exe_dir", return_value=FAKE_DIR):
        opts = dl.build_opts(OUT_DIR, "sample")
    assert opts["outtmpl"] == str(Path(OUT_DIR) / "sample.%(ext)s")
    assert opts["ffmpeg_location"] == FAKE_DIR
    assert opts["format"] == "bv*+ba/b"
    assert opts["merge_output_format"] == "mp4"


def test_default_ffmpeg_locator_constructed_when_none() -> None:
    """Omitting the locator constructs a FfmpegLocator internally."""
    dl = BaseDownloader(ConfigManager(data={"version": "1.00"}))
    from ytdl.infra.ffmpeg import FfmpegLocator

    assert isinstance(dl._ffmpeg, FfmpegLocator)
