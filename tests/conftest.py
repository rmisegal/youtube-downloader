"""Shared pytest fixtures for the ytdl test suite.

All external boundaries (yt-dlp, ffmpeg) are mocked here so unit tests never touch
the network or a real FFmpeg binary. Reused by later test waves.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ytdl.shared.config import ConfigManager

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CONFIG_DIR = _REPO_ROOT / "config"

# In-memory config mirroring config/setup.json for hermetic tests.
SAMPLE_CONFIG_DATA: dict = {
    "version": "1.00",
    "paths": {"output_dir": "./downloads"},
    "defaults": {"resolution": None, "sub_lang": "en", "modes": ["video"]},
    "audio": {"codec": "mp3", "quality": "192"},
    "subtitles": {"format": "srt", "include_auto": True},
    "ffmpeg": {"location": "auto"},
}

FAKE_FFMPEG_EXE = "/fake/path/to/ffmpeg"


@pytest.fixture
def mock_ytdl() -> MagicMock:
    """A MagicMock standing in for ``yt_dlp.YoutubeDL``.

    The mock is callable (acts as the class) and its return value behaves like a
    ``YoutubeDL`` instance supporting the context-manager protocol plus
    ``extract_info`` and ``download``.
    """
    ydl_instance = MagicMock(name="YoutubeDL_instance")
    ydl_instance.extract_info.return_value = {
        "id": "abc123",
        "title": "Sample Video",
        "ext": "mp4",
    }
    ydl_instance.download.return_value = 0
    ydl_instance.__enter__.return_value = ydl_instance
    ydl_instance.__exit__.return_value = False

    ydl_class = MagicMock(name="YoutubeDL_class", return_value=ydl_instance)
    return ydl_class


@pytest.fixture
def mock_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> str:
    """Patch ``imageio_ffmpeg.get_ffmpeg_exe`` to return a fake path.

    Returns the fake ffmpeg executable path so tests can assert against it.
    Patches the symbol in the imageio_ffmpeg module itself so any importer sees it.
    """
    import imageio_ffmpeg

    monkeypatch.setattr(
        imageio_ffmpeg, "get_ffmpeg_exe", lambda: FAKE_FFMPEG_EXE, raising=True
    )
    return FAKE_FFMPEG_EXE


@pytest.fixture
def sample_config() -> ConfigManager:
    """A ``ConfigManager`` backed by the in-memory sample config (no file I/O)."""
    return ConfigManager(data=dict(SAMPLE_CONFIG_DATA))


@pytest.fixture
def real_config() -> ConfigManager:
    """A ``ConfigManager`` pointed at the real repo ``config/setup.json``."""
    return ConfigManager(file_name="setup.json", config_dir=_CONFIG_DIR)


@pytest.fixture
def real_rate_limits() -> ConfigManager:
    """A ``ConfigManager`` pointed at the real repo ``config/rate_limits.json``."""
    return ConfigManager(file_name="rate_limits.json", config_dir=_CONFIG_DIR)


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """A temporary output directory for download artifacts."""
    out = tmp_path / "downloads"
    out.mkdir(parents=True, exist_ok=True)
    return out
