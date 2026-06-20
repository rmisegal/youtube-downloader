"""Unit tests for ytdl.shared.throttle.ThrottlePolicy.

Uses an in-memory ConfigManager(data=...); no network or files touched.
"""

from __future__ import annotations

import pytest

from ytdl.shared.config import ConfigManager
from ytdl.shared.throttle import ThrottlePolicy, _as_float, _as_int, _parse_rate

_BASE_KEY = "rate_limits.services.youtube.download"

_FULL_DOWNLOAD: dict = {
    "limit_rate": "5M",
    "throttled_rate": "100K",
    "sleep_requests_seconds": 1.0,
    "sleep_interval_seconds": 3.0,
    "max_sleep_interval_seconds": 8.0,
    "concurrent_fragments": 1,
    "retries": 10,
    "fragment_retries": 10,
}


def _config(download: dict | None) -> ConfigManager:
    """Build a ConfigManager whose download block is ``download``."""
    youtube: dict = {}
    if download is not None:
        youtube["download"] = download
    data = {"rate_limits": {"services": {"youtube": youtube}}}
    return ConfigManager(data=data)


def test_full_config_maps_all_keys() -> None:
    policy = ThrottlePolicy(_config(_FULL_DOWNLOAD))
    opts = policy.ydl_opts()
    assert opts == {
        "ratelimit": 5 * 1024 * 1024,
        "throttledratelimit": 100 * 1024,
        "sleep_interval_requests": 1.0,
        "sleep_interval": 3.0,
        "max_sleep_interval": 8.0,
        "concurrent_fragment_downloads": 1,
        "retries": 10,
        "fragment_retries": 10,
    }


def test_rate_values() -> None:
    opts = ThrottlePolicy(_config(_FULL_DOWNLOAD)).ydl_opts()
    assert opts["ratelimit"] == 5 * 1024 * 1024
    assert opts["throttledratelimit"] == 100 * 1024


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("5M", 5242880),
        ("100K", 102400),
        ("1G", 1073741824),
        (2048, 2048),
        ("", None),
        (None, None),
    ],
)
def test_parse_rate(value: object, expected: int | None) -> None:
    assert _parse_rate(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, None),  # bool rejected
        (False, None),
        (3.9, 3),  # float -> int truncation
        ("2048", 2048),  # plain digit string
        ("  ", None),  # blank -> None
        ("abc", None),  # unparseable -> None
        ("xM", None),  # bad number before known suffix -> None
        ("5Z", None),  # unknown suffix, unparseable whole -> None
    ],
)
def test_parse_rate_branches(value: object, expected: int | None) -> None:
    assert _parse_rate(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (True, None),
        ("x", None),
        (object(), None),
        ("3.5", 3.5),
    ],
)
def test_as_float_branches(value: object, expected: float | None) -> None:
    assert _as_float(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (False, None),
        ("x", None),
        (object(), None),
        ("4", 4),
    ],
)
def test_as_int_branches(value: object, expected: int | None) -> None:
    assert _as_int(value) == expected


def test_missing_download_block_returns_empty() -> None:
    assert ThrottlePolicy(_config(None)).ydl_opts() == {}


def test_partial_config_emits_only_present_keys() -> None:
    opts = ThrottlePolicy(
        _config({"limit_rate": "5M", "retries": 4})
    ).ydl_opts()
    assert opts == {"ratelimit": 5 * 1024 * 1024, "retries": 4}
    assert all(value is not None for value in opts.values())


def test_value_types() -> None:
    opts = ThrottlePolicy(_config(_FULL_DOWNLOAD)).ydl_opts()
    assert isinstance(opts["sleep_interval_requests"], float)
    assert isinstance(opts["sleep_interval"], float)
    assert isinstance(opts["max_sleep_interval"], float)
    assert isinstance(opts["concurrent_fragment_downloads"], int)
    assert isinstance(opts["retries"], int)
    assert not isinstance(opts["retries"], bool)


def test_custom_base_key() -> None:
    data = {"dl": {"limit_rate": "100K"}}
    opts = ThrottlePolicy(ConfigManager(data=data), base_key="dl").ydl_opts()
    assert opts == {"ratelimit": 100 * 1024}
