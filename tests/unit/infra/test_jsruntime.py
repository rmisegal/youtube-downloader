"""Unit tests for :func:`ytdl.infra.jsruntime.detect_runtime`.

All tests patch ``shutil.which`` via a name->path/None mapping. No real
subprocess, no PATH dependence.
"""

from __future__ import annotations

from collections.abc import Mapping
from unittest.mock import patch

import pytest

from ytdl.infra.jsruntime import SUPPORTED_RUNTIMES, detect_runtime

_FAKE_PATH = "/fake/bin/runtime"


def _which(available: Mapping[str, bool]):
    """Build a ``shutil.which`` side_effect from a name->present mapping."""

    def side_effect(name: str) -> str | None:
        return _FAKE_PATH if available.get(name, False) else None

    return side_effect


def _patch(available: Mapping[str, bool]):
    return patch("ytdl.infra.jsruntime.shutil.which", side_effect=_which(available))


def test_auto_picks_first_available_by_priority() -> None:
    """deno absent, node present -> node (next in priority order)."""
    with _patch({"deno": False, "node": True, "bun": True}):
        assert detect_runtime("auto") == {"node": {}}


def test_auto_prefers_deno_when_present() -> None:
    """deno is highest priority and chosen when available."""
    with _patch({"deno": True, "node": True}):
        assert detect_runtime("auto") == {"deno": {}}


def test_auto_returns_empty_when_none_on_path() -> None:
    """No runtime on PATH -> empty dict."""
    with _patch({}):
        assert detect_runtime("auto") == {}


def test_explicit_node_present() -> None:
    """Explicit supported name present -> that entry."""
    with _patch({"deno": True, "node": True}):
        assert detect_runtime("node") == {"node": {}}


def test_explicit_node_absent() -> None:
    """Explicit supported name absent -> empty (ignores other runtimes)."""
    with _patch({"deno": True, "node": False}):
        assert detect_runtime("node") == {}


@pytest.mark.parametrize("token", ["none", "off", "", None])
def test_disable_tokens_return_empty(token: str | None) -> None:
    """Disable tokens never touch PATH and return empty."""
    with _patch({"deno": True}):
        assert detect_runtime(token) == {}


def test_unsupported_name_returns_empty() -> None:
    """Unsupported explicit name returns empty without raising."""
    with _patch({"v8": True}):
        assert detect_runtime("v8") == {}


def test_default_preference_is_auto() -> None:
    """No-arg call behaves like 'auto'."""
    with _patch({"deno": True}):
        assert detect_runtime() == {"deno": {}}


def test_supported_runtimes_constant() -> None:
    """Constant lists exactly the four supported runtimes, deno first."""
    assert SUPPORTED_RUNTIMES == ("deno", "node", "bun", "quickjs")
