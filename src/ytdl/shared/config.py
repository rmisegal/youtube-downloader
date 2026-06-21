"""ConfigManager: load a versioned JSON config and read values via dotted keys."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ytdl.shared.errors import ConfigNotFoundError, ConfigVersionError

# Repo `config/` dir: src/ytdl/shared/config.py -> parents[3] == repo root.
_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


class ConfigManager:
    """Loads a JSON config file and exposes dotted-key lookups with defaults.

    The config file must carry a ``"version"`` whose value is one of
    ``SUPPORTED_CONFIG_VERSIONS``; otherwise validation raises
    :class:`ConfigVersionError`.
    """

    SUPPORTED_CONFIG_VERSIONS: list[str] = [
        "1.00", "1.01", "1.02", "1.03", "1.04", "1.05", "1.06",
    ]
    VERSION_KEY: str = "version"

    def __init__(
        self,
        file_name: str = "setup.json",
        config_dir: Path | str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Build from a JSON file under ``config_dir`` or from an in-memory dict.

        Args:
            file_name: Config file name to load (ignored when ``data`` is given).
            config_dir: Directory holding the config file. Defaults to repo ``config/``.
            data: Pre-built config dict; bypasses file loading (for tests).
        """
        if data is not None:
            self._data: dict[str, Any] = data
            self._path: Path | None = None
        else:
            base = Path(config_dir) if config_dir is not None else _DEFAULT_CONFIG_DIR
            self._path = base / file_name
            self._data = self._load(self._path)

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        """Read and parse a JSON config file."""
        if not path.is_file():
            raise ConfigNotFoundError(f"Config file not found: {path}")
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def get(self, key: str, default: Any = None) -> Any:
        """Return a value by dotted ``key`` (e.g. ``"audio.codec"``).

        Returns ``default`` if any segment is missing or a non-dict is traversed.
        """
        node: Any = self._data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    @property
    def version(self) -> Any:
        """The config file's declared version (or ``None`` if absent)."""
        return self._data.get(self.VERSION_KEY)

    def validate_config_version(self) -> None:
        """Raise :class:`ConfigVersionError` if the version is unsupported."""
        version = self.version
        if version not in self.SUPPORTED_CONFIG_VERSIONS:
            raise ConfigVersionError(
                f"Unsupported config version {version!r}; "
                f"supported: {self.SUPPORTED_CONFIG_VERSIONS}"
            )

    @property
    def data(self) -> dict[str, Any]:
        """The raw config mapping."""
        return self._data
