"""Detect an installed JavaScript runtime for yt-dlp.

yt-dlp 2026.06.09 warns "No supported JavaScript runtime could be found"
unless its ``js_runtimes`` option is configured. That option is a dict mapping
a runtime name to a (possibly empty) config dict, e.g. ``{"deno": {}}``.

This module auto-detects the first available runtime on ``PATH`` so the warning
disappears and all formats are available. Pure stdlib (``shutil``); no yt-dlp
import. The caller passes the returned dict as ``js_runtimes`` (omitting the
option entirely when an empty dict is returned).
"""

from __future__ import annotations

import shutil

# Supported runtime names, in detection priority order (deno first).
SUPPORTED_RUNTIMES: tuple[str, ...] = ("deno", "node", "bun", "quickjs")
PRIORITY_ORDER: tuple[str, ...] = SUPPORTED_RUNTIMES

# Tokens that explicitly disable JS-runtime configuration.
_DISABLE_TOKENS: frozenset[str] = frozenset({"none", "off", ""})


def detect_runtime(preference: str | None = "auto") -> dict[str, dict]:
    """Resolve a yt-dlp ``js_runtimes`` dict from a preference string.

    Args:
        preference: ``"auto"`` to pick the first available runtime by priority;
            a specific supported name (e.g. ``"node"``) to use only that one;
            or a disable token (``"none"``, ``"off"``, ``""``, ``None``) to skip
            runtime configuration entirely.

    Returns:
        ``{name: {}}`` for the resolved runtime, or ``{}`` when disabled, when
        no runtime is found, or when an unsupported name is given. An empty dict
        signals the caller to omit the ``js_runtimes`` option.
    """
    if preference is None or preference in _DISABLE_TOKENS:
        return {}
    if preference == "auto":
        return _first_available()
    if preference in SUPPORTED_RUNTIMES:
        return _entry_if_present(preference)
    # Unsupported explicit name: do not raise, just decline to configure.
    return {}


def _first_available() -> dict[str, dict]:
    """Return ``{name: {}}`` for the first runtime found on PATH, else ``{}``."""
    for name in PRIORITY_ORDER:
        entry = _entry_if_present(name)
        if entry:
            return entry
    return {}


def _entry_if_present(name: str) -> dict[str, dict]:
    """Return ``{name: {}}`` if ``name`` resolves on PATH, else ``{}``."""
    if shutil.which(name) is not None:
        return {name: {}}
    return {}
