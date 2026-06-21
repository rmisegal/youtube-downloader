"""Unit tests for ``BaseDownloader`` ``extra_opts`` injection.

``FfmpegLocator.exe`` is patched to a fake path; env vars are cleared. No real
FFmpeg, no network.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import pytest

from ytdl.constants import ENV_COOKIES_FILE, ENV_PROXY
from ytdl.services.base import BaseDownloader
from ytdl.shared.config import ConfigManager

FAKE_EXE = os.path.join(os.sep, "fake", "bin", "ffmpeg.exe")
OUT_DIR = os.path.join(os.sep, "out")
EXTRA: dict[str, Any] = {"ratelimit": 123, "js_runtimes": {"node": {}}}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_PROXY, raising=False)
    monkeypatch.delenv(ENV_COOKIES_FILE, raising=False)


def _build(extra: dict[str, Any]) -> dict[str, Any]:
    dl = BaseDownloader(ConfigManager(data={"version": "1.00"}), extra_opts=extra)
    with patch("ytdl.infra.ffmpeg.FfmpegLocator.exe", return_value=FAKE_EXE):
        return dl.build_base_opts(OUT_DIR, "sample")


def test_extra_opts_included() -> None:
    opts = _build(EXTRA)
    assert opts["ratelimit"] == 123
    assert opts["js_runtimes"] == {"node": {}}


def test_base_essentials_still_present() -> None:
    opts = _build(EXTRA)
    assert "outtmpl" in opts
    assert opts["ffmpeg_location"] == FAKE_EXE


def test_extra_opts_do_not_override_base_essentials() -> None:
    opts = _build({"outtmpl": "HIJACKED", "ffmpeg_location": "HIJACKED"})
    assert opts["outtmpl"] != "HIJACKED"
    assert opts["ffmpeg_location"] == FAKE_EXE


def test_none_extra_opts_yields_only_base() -> None:
    dl = BaseDownloader(ConfigManager(data={"version": "1.00"}), extra_opts=None)
    with patch("ytdl.infra.ffmpeg.FfmpegLocator.exe", return_value=FAKE_EXE):
        opts = dl.build_base_opts(OUT_DIR, "x")
    # base = output + ffmpeg + the clean progress hook (noprogress + progress_hooks).
    assert set(opts) == {"outtmpl", "ffmpeg_location", "noprogress", "progress_hooks"}
    assert opts["noprogress"] is True and callable(opts["progress_hooks"][0])
