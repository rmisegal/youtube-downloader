"""Unit tests for ytdl.shared.config.ConfigManager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ytdl.shared.config import ConfigManager
from ytdl.shared.errors import ConfigNotFoundError, ConfigVersionError


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_loads_json_file(tmp_path: Path) -> None:
    cfg_file = tmp_path / "setup.json"
    _write_json(cfg_file, {"version": "1.00", "audio": {"codec": "mp3"}})

    cfg = ConfigManager(file_name="setup.json", config_dir=tmp_path)

    assert cfg.version == "1.00"
    assert cfg.data["audio"]["codec"] == "mp3"


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigNotFoundError):
        ConfigManager(file_name="nope.json", config_dir=tmp_path)


def test_get_dotted_hit() -> None:
    cfg = ConfigManager(data={"version": "1.00", "audio": {"quality": "192"}})

    assert cfg.get("audio.quality") == "192"


def test_get_nested_value() -> None:
    cfg = ConfigManager(
        data={"rate_limits": {"services": {"youtube": {"requests_per_minute": 20}}}}
    )

    assert cfg.get("rate_limits.services.youtube.requests_per_minute") == 20


def test_get_missing_returns_default() -> None:
    cfg = ConfigManager(data={"version": "1.00"})

    assert cfg.get("paths.output_dir", "./downloads") == "./downloads"
    assert cfg.get("nope") is None


def test_get_traverses_non_dict_returns_default() -> None:
    cfg = ConfigManager(data={"audio": "not-a-dict"})

    assert cfg.get("audio.codec", "fallback") == "fallback"


def test_version_validation_success() -> None:
    cfg = ConfigManager(data={"version": "1.00"})

    # Should not raise.
    cfg.validate_config_version()


def test_version_mismatch_raises() -> None:
    cfg = ConfigManager(data={"version": "9.99"})

    with pytest.raises(ConfigVersionError):
        cfg.validate_config_version()


def test_missing_version_raises() -> None:
    cfg = ConfigManager(data={})

    with pytest.raises(ConfigVersionError):
        cfg.validate_config_version()


def test_real_setup_config_loads_and_validates() -> None:
    repo_config = Path(__file__).resolve().parents[3] / "config"
    cfg = ConfigManager(file_name="setup.json", config_dir=repo_config)

    cfg.validate_config_version()
    assert cfg.get("paths.output_dir") == "./downloads"
    assert cfg.get("defaults.sub_lang") == "en"
    assert cfg.get("audio.codec") == "mp3"


def test_real_rate_limits_config_loads_and_validates() -> None:
    repo_config = Path(__file__).resolve().parents[3] / "config"
    cfg = ConfigManager(file_name="rate_limits.json", config_dir=repo_config)

    cfg.validate_config_version()
    assert cfg.get("rate_limits.services.youtube.requests_per_minute") == 20
    assert cfg.get("queue.overflow_strategy") == "reject_oldest"
