"""Unit tests for :class:`ytdl.services.video.VideoDownloader`.

``FfmpegLocator.exe_dir`` is patched to a fake dir and env vars are cleared via
``monkeypatch`` — no real FFmpeg, no network. The tests assert both the
video-specific ``_mode_opts`` hook and that it composes with the base options
through ``build_opts``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from ytdl.constants import ENV_COOKIES_FILE, ENV_PROXY
from ytdl.services.video import VideoDownloader
from ytdl.shared.config import ConfigManager

FAKE_DIR = os.path.join(os.sep, "fake", "bin")
OUT_DIR = os.path.join(os.sep, "out")


@pytest.fixture
def downloader(monkeypatch: pytest.MonkeyPatch) -> VideoDownloader:
    """A VideoDownloader with a clean env (no proxy/cookies)."""
    monkeypatch.delenv(ENV_PROXY, raising=False)
    monkeypatch.delenv(ENV_COOKIES_FILE, raising=False)
    return VideoDownloader(ConfigManager(data={"version": "1.00"}))


def _build(dl: VideoDownloader, **kwargs: Any) -> dict[str, Any]:
    with patch("ytdl.infra.ffmpeg.FfmpegLocator.exe_dir", return_value=FAKE_DIR):
        return dl.build_opts(OUT_DIR, "sample", **kwargs)


def test_mode_opts_capped_format_with_resolution(
    downloader: VideoDownloader,
) -> None:
    """A 720 resolution yields a height-capped format selector."""
    opts = downloader._mode_opts(resolution=720)
    assert opts["format"] == "bv*[height<=720]+ba/b"
    assert opts["merge_output_format"] == "mp4"


def test_mode_opts_best_format_when_none(downloader: VideoDownloader) -> None:
    """No resolution (None) selects best quality with no cap."""
    opts = downloader._mode_opts(resolution=None)
    assert opts["format"] == "bv*+ba/b"
    assert opts["merge_output_format"] == "mp4"


def test_mode_opts_best_format_when_absent(downloader: VideoDownloader) -> None:
    """Omitting the resolution kwarg behaves like None (best)."""
    opts = downloader._mode_opts()
    assert opts["format"] == "bv*+ba/b"


def test_build_opts_capped_composes_with_base(
    downloader: VideoDownloader,
) -> None:
    """build_opts(resolution=1080) merges base keys with the capped format."""
    opts = _build(downloader, resolution=1080)
    assert opts["format"] == "bv*[height<=1080]+ba/b"
    assert opts["merge_output_format"] == "mp4"
    assert opts["outtmpl"] == str(Path(OUT_DIR) / "sample.%(ext)s")
    assert opts["ffmpeg_location"] == FAKE_DIR


def test_build_opts_best_composes_with_base(downloader: VideoDownloader) -> None:
    """build_opts(resolution=None) still includes the base keys."""
    opts = _build(downloader, resolution=None)
    assert opts["format"] == "bv*+ba/b"
    assert opts["merge_output_format"] == "mp4"
    assert opts["outtmpl"] == str(Path(OUT_DIR) / "sample.%(ext)s")
    assert opts["ffmpeg_location"] == FAKE_DIR


@pytest.mark.parametrize("res", [144, 720, 1080, 2160])
def test_build_opts_boundary_resolutions(
    downloader: VideoDownloader, res: int
) -> None:
    """Various height caps are templated correctly into the selector."""
    opts = _build(downloader, resolution=res)
    assert opts["format"] == f"bv*[height<={res}]+ba/b"
    assert opts["merge_output_format"] == "mp4"
