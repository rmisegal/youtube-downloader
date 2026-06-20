"""ThrottlePolicy: build yt-dlp throttle opts from the rate_limits config.

Pure module (no yt-dlp import). Maps the config block at
``rate_limits.services.youtube.download`` onto verified yt-dlp option keys.
"""

from __future__ import annotations

from typing import Any

from ytdl.shared.config import ConfigManager

_DEFAULT_BASE_KEY = "rate_limits.services.youtube.download"

# Binary (1024-based) suffix multipliers, case-insensitive.
_RATE_MULTIPLIERS: dict[str, int] = {
    "K": 1024,
    "M": 1024 * 1024,
    "G": 1024 * 1024 * 1024,
}


def _parse_rate(value: Any) -> int | None:
    """Parse a rate like ``"5M"``/``"100K"``/``"1G"``/``2048`` to bytes/sec.

    Suffixes K/M/G are binary (1024) multipliers and case-insensitive.
    ``None`` or an empty/blank value yields ``None``. Plain ints/digit
    strings pass through. Unparseable values yield ``None``.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    suffix = text[-1].upper()
    if suffix in _RATE_MULTIPLIERS:
        number = text[:-1].strip()
        try:
            return int(float(number) * _RATE_MULTIPLIERS[suffix])
        except ValueError:
            return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _as_float(value: Any) -> float | None:
    """Coerce ``value`` to ``float`` or ``None`` for missing/bad types."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    """Coerce ``value`` to ``int`` or ``None`` for missing/bad types."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class ThrottlePolicy:
    """Translate the download throttle config into a yt-dlp opts dict."""

    def __init__(
        self,
        config: ConfigManager,
        base_key: str = _DEFAULT_BASE_KEY,
    ) -> None:
        """Bind a :class:`ConfigManager` and the dotted base key to read."""
        self._config = config
        self._base_key = base_key

    def _get(self, name: str) -> Any:
        """Read ``name`` under the configured base key (or ``None``)."""
        return self._config.get(f"{self._base_key}.{name}")

    def ydl_opts(self) -> dict[str, Any]:
        """Return yt-dlp throttle opts, omitting any missing/None values."""
        opts: dict[str, Any] = {}
        self._set(opts, "ratelimit", _parse_rate(self._get("limit_rate")))
        self._set(
            opts,
            "throttledratelimit",
            _parse_rate(self._get("throttled_rate")),
        )
        self._set(
            opts,
            "sleep_interval_requests",
            _as_float(self._get("sleep_requests_seconds")),
        )
        self._set(
            opts,
            "sleep_interval",
            _as_float(self._get("sleep_interval_seconds")),
        )
        self._set(
            opts,
            "max_sleep_interval",
            _as_float(self._get("max_sleep_interval_seconds")),
        )
        self._set(
            opts,
            "concurrent_fragment_downloads",
            _as_int(self._get("concurrent_fragments")),
        )
        self._set(opts, "retries", _as_int(self._get("retries")))
        self._set(
            opts,
            "fragment_retries",
            _as_int(self._get("fragment_retries")),
        )
        return opts

    @staticmethod
    def _set(opts: dict[str, Any], key: str, value: Any) -> None:
        """Assign ``value`` to ``key`` only when it is not ``None``."""
        if value is not None:
            opts[key] = value
