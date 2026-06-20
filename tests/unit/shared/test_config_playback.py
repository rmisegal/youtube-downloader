"""Config tests for the v1.03 ``sample`` + ``render`` blocks (PRD-playlist §8)."""

from __future__ import annotations

from pathlib import Path

from ytdl.shared.config import ConfigManager

_REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


def _setup() -> ConfigManager:
    return ConfigManager(file_name="setup.json", config_dir=_REPO_CONFIG)


def test_setup_version_1_03_validates() -> None:
    cfg = _setup()

    cfg.validate_config_version()
    assert cfg.version == "1.03"


def test_sample_block_defaults() -> None:
    cfg = _setup()

    assert cfg.get("sample.play_seconds") == 10
    assert cfg.get("sample.mid_band_low") == 0.25
    assert cfg.get("sample.mid_band_high") == 0.75
    assert cfg.get("sample.loop") is True


def test_render_block_defaults() -> None:
    cfg = _setup()

    assert cfg.get("render.video_codec") == "libx264"
    assert cfg.get("render.audio_codec") == "aac"
    assert cfg.get("render.container") == "mp4"


def test_rate_limits_version_1_03() -> None:
    cfg = ConfigManager(file_name="rate_limits.json", config_dir=_REPO_CONFIG)

    cfg.validate_config_version()
    assert cfg.version == "1.03"
