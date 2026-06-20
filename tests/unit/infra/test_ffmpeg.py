"""Unit tests for :class:`ytdl.infra.ffmpeg.FfmpegLocator`.

All tests mock ``imageio_ffmpeg.get_ffmpeg_exe`` — no real FFmpeg, no network.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from ytdl.infra.ffmpeg import AUTO_LOCATION, FfmpegLocator

FAKE_EXE = os.path.join(os.sep, "fake", "bin", "ffmpeg.exe")
FAKE_DIR = os.path.join(os.sep, "fake", "bin")


def test_exe_returns_imageio_path_when_auto() -> None:
    """``exe()`` returns the imageio-resolved path under the default 'auto'."""
    with patch("imageio_ffmpeg.get_ffmpeg_exe", return_value=FAKE_EXE):
        assert FfmpegLocator().exe() == FAKE_EXE


def test_exe_dir_is_parent_of_exe() -> None:
    """``exe_dir()`` returns the parent directory of the executable."""
    with patch("imageio_ffmpeg.get_ffmpeg_exe", return_value=FAKE_EXE):
        assert FfmpegLocator().exe_dir() == FAKE_DIR


def test_default_location_is_auto() -> None:
    """No-arg and ``None`` constructions both default to 'auto' resolution."""
    with patch("imageio_ffmpeg.get_ffmpeg_exe", return_value=FAKE_EXE) as mock:
        assert FfmpegLocator(None).exe() == FAKE_EXE
        assert AUTO_LOCATION == "auto"
        mock.assert_called_once()


def test_exe_is_memoized() -> None:
    """``get_ffmpeg_exe`` is called only once across multiple ``exe()`` calls."""
    locator = FfmpegLocator()
    with patch("imageio_ffmpeg.get_ffmpeg_exe", return_value=FAKE_EXE) as mock:
        first = locator.exe()
        second = locator.exe()
        locator.exe_dir()
    assert first == second == FAKE_EXE
    mock.assert_called_once()


def test_explicit_location_bypasses_imageio() -> None:
    """An explicit configured path is returned without importing imageio."""
    explicit = os.path.join(os.sep, "opt", "ffmpeg", "ffmpeg")
    with patch("imageio_ffmpeg.get_ffmpeg_exe") as mock:
        locator = FfmpegLocator(location=explicit)
        assert locator.exe() == explicit
        assert locator.exe_dir() == os.path.dirname(explicit)
    mock.assert_not_called()


def test_uses_mock_ffmpeg_fixture(mock_ffmpeg: str) -> None:
    """The shared ``mock_ffmpeg`` conftest fixture drives 'auto' resolution."""
    assert FfmpegLocator().exe() == mock_ffmpeg
