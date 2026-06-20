"""Unit tests for :class:`ytdl.services.audio.AudioDownloader`.

``FfmpegLocator.exe`` is patched to a fake dir; the config is driven via an
in-memory :class:`ConfigManager` — no real FFmpeg, no network.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

from ytdl.services.audio import AudioDownloader
from ytdl.shared.config import ConfigManager

FAKE_DIR = os.path.join(os.sep, "fake", "bin")
OUT_DIR = os.path.join(os.sep, "out")


def _make(audio: dict[str, Any] | None = None) -> AudioDownloader:
    """An AudioDownloader backed by an in-memory config."""
    data: dict[str, Any] = {"version": "1.00"}
    if audio is not None:
        data["audio"] = audio
    return AudioDownloader(ConfigManager(data=data))


def _build(dl: AudioDownloader, name: str | None = "sample") -> dict[str, Any]:
    with patch("ytdl.infra.ffmpeg.FfmpegLocator.exe", return_value=FAKE_DIR):
        return dl.build_opts(OUT_DIR, name)


def _extract_pp(opts: dict[str, Any]) -> dict[str, Any]:
    pps = opts["postprocessors"]
    return next(pp for pp in pps if pp["key"] == "FFmpegExtractAudio")


def test_postprocessor_present_with_extract_audio_key() -> None:
    """opts contain an ``FFmpegExtractAudio`` post-processor."""
    opts = _build(_make({"codec": "mp3", "quality": "192"}))
    assert _extract_pp(opts)["key"] == "FFmpegExtractAudio"


def test_codec_and_quality_match_configured_values() -> None:
    """preferredcodec/preferredquality equal the configured values."""
    opts = _build(_make({"codec": "mp3", "quality": "192"}))
    pp = _extract_pp(opts)
    assert pp["preferredcodec"] == "mp3"
    assert pp["preferredquality"] == "192"


def test_changing_config_changes_opts() -> None:
    """A different config codec/quality yields different opts (config-driven)."""
    pp = _extract_pp(_build(_make({"codec": "wav", "quality": "0"})))
    assert pp["preferredcodec"] == "wav"
    assert pp["preferredquality"] == "0"


def test_defaults_used_when_audio_section_absent() -> None:
    """Missing ``audio`` config falls back to mp3 / 192 (not crash)."""
    pp = _extract_pp(_build(_make(audio=None)))
    assert pp["preferredcodec"] == "mp3"
    assert pp["preferredquality"] == "192"


def test_default_quality_used_when_only_codec_set() -> None:
    """Partial ``audio`` config: missing quality falls back to default."""
    pp = _extract_pp(_build(_make({"codec": "flac"})))
    assert pp["preferredcodec"] == "flac"
    assert pp["preferredquality"] == "192"


def test_merged_opts_include_base_keys() -> None:
    """Merged opts still carry the base ``outtmpl`` and ``ffmpeg_location``."""
    opts = _build(_make({"codec": "mp3", "quality": "192"}), name="sample")
    assert opts["outtmpl"] == str(Path(OUT_DIR) / "sample.%(ext)s")
    assert opts["ffmpeg_location"] == FAKE_DIR


def test_exactly_one_extract_audio_postprocessor() -> None:
    """Edge: exactly one post-processor, the audio extractor."""
    opts = _build(_make({"codec": "mp3", "quality": "192"}))
    assert len(opts["postprocessors"]) == 1


def test_mode_opts_only_adds_postprocessors() -> None:
    """The hook contributes only the ``postprocessors`` key (overrides only)."""
    dl = _make({"codec": "mp3", "quality": "192"})
    assert set(dl._mode_opts()) == {"postprocessors"}
