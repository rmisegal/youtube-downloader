"""Unit tests for :mod:`ytdl.shared.logsetup` (rotating file + console handlers)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from ytdl.shared import logsetup
from ytdl.shared.config import ConfigManager


def _config(directory) -> ConfigManager:
    return ConfigManager(
        data={
            "version": "1.03",
            "logging": {
                "dir": str(directory),
                "app_file": "ytdl.log",
                "subprocess_file": "ffmpeg.log",
                "max_bytes": 4096,
                "console_level": "ERROR",
            },
        }
    )


def _handlers():
    logger = logging.getLogger("ytdl")
    files = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
    consoles = [
        h
        for h in logger.handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
    ]
    return files, consoles


def test_configure_logging_default_console_is_error_level(tmp_path) -> None:
    logsetup.configure_logging(_config(tmp_path / "logs"))
    files, consoles = _handlers()
    assert len(files) == 1
    assert files[0].level == logging.DEBUG
    assert len(consoles) == 1
    assert consoles[0].level == logging.ERROR
    logging.getLogger("ytdl").handlers.clear()


def test_configure_logging_verbose_console_is_info_level(tmp_path) -> None:
    logsetup.configure_logging(_config(tmp_path / "logs"), verbose=True)
    _files, consoles = _handlers()
    assert consoles[0].level == logging.INFO
    logging.getLogger("ytdl").handlers.clear()


def test_configure_logging_is_idempotent(tmp_path) -> None:
    cfg = _config(tmp_path / "logs")
    logsetup.configure_logging(cfg)
    logsetup.configure_logging(cfg)
    files, consoles = _handlers()
    assert len(files) == 1 and len(consoles) == 1
    logging.getLogger("ytdl").handlers.clear()


def test_configure_logging_creates_dir(tmp_path) -> None:
    log_dir = tmp_path / "logs"
    assert not log_dir.exists()
    logsetup.configure_logging(_config(log_dir))
    assert log_dir.is_dir()
    logging.getLogger("ytdl").handlers.clear()


def test_subprocess_log_path_under_dir_and_creates_it(tmp_path) -> None:
    log_dir = tmp_path / "logs"
    path = logsetup.subprocess_log_path(_config(log_dir))
    assert path == log_dir / "ffmpeg.log"
    assert log_dir.is_dir()
