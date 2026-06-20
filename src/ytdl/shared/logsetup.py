"""Application + subprocess logging setup (clean terminal, rotating file).

The terminal shows ONLY errors by default; all app logs (DEBUG+) go to a
size-capped rotating file (FIFO). FFmpeg/VLC subprocess stderr is redirected
to a separate subprocess log file (path from :func:`subprocess_log_path`).
Config-driven via the ``logging`` block (no hardcoded tunables).
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# src/ytdl/shared/logsetup.py -> parents[3] == repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOGGER_NAME = "ytdl"

_DEFAULTS = {
    "dir": "logs",
    "app_file": "ytdl.log",
    "subprocess_file": "ffmpeg.log",
    "max_bytes": 1048576,
    "console_level": "ERROR",
}
_CONSOLE_FORMAT = "%(levelname)s %(name)s: %(message)s"
_FILE_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def _get(config: Any, key: str) -> Any:
    """Read ``logging.<key>`` from ``config`` (or its baked-in default)."""
    default = _DEFAULTS[key]
    if config is None:
        return default
    return config.get(f"logging.{key}", default)


def _resolve_dir(config: Any) -> Path:
    """Resolve the log directory (relative paths are repo-root-anchored)."""
    raw = Path(str(_get(config, "dir")))
    directory = raw if raw.is_absolute() else _REPO_ROOT / raw
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def configure_logging(config: Any, *, verbose: bool = False) -> None:
    """Idempotently attach a rotating file handler + a console handler.

    The file handler captures all app logs at DEBUG into a size-capped
    rotating file. The console handler (stderr) shows ``INFO`` when
    ``verbose`` else the configured ``console_level`` (default ``ERROR``).
    """
    directory = _resolve_dir(config)
    logger = logging.getLogger(_LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    file_handler = RotatingFileHandler(
        directory / str(_get(config, "app_file")),
        maxBytes=int(_get(config, "max_bytes")),
        backupCount=1,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
    logger.addHandler(file_handler)

    console = logging.StreamHandler(sys.stderr)
    level = logging.INFO if verbose else _console_level(config)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
    logger.addHandler(console)


def _console_level(config: Any) -> int:
    """Map the configured ``console_level`` name to a logging level int."""
    name = str(_get(config, "console_level")).upper()
    return getattr(logging, name, logging.ERROR)


def subprocess_log_path(config: Any) -> Path:
    """Ensure the log dir exists and return the subprocess log file path."""
    directory = _resolve_dir(config)
    return directory / str(_get(config, "subprocess_file"))
