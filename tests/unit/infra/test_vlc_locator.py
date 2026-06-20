"""Unit tests for :class:`ytdl.infra.playback.vlc_locator.VlcLocator`.

No real VLC is touched: ``shutil.which`` and ``os.path.exists`` are patched, and
the lazy ``import vlc`` is satisfied by a fake module injected into
``sys.modules``.
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest

from ytdl.infra.playback import vlc_locator as mod
from ytdl.infra.playback.vlc_locator import VlcLocator
from ytdl.shared.errors import PlaybackDependencyError

WHICH = "ytdl.infra.playback.vlc_locator.shutil.which"
EXISTS = "ytdl.infra.playback.vlc_locator.os.path.exists"


def _fake_vlc(instance=None) -> ModuleType:
    """Build a fake ``vlc`` module with a callable ``Instance``."""
    module = ModuleType("vlc")
    module.Instance = instance or (lambda *a, **k: SimpleNamespace())
    return module


def test_vlc_binary_returns_which_path() -> None:
    """``vlc_binary`` returns the ``which`` result when present."""
    with patch(WHICH, return_value="/usr/bin/vlc"):
        assert VlcLocator().vlc_binary() == "/usr/bin/vlc"


def test_vlc_binary_falls_back_to_windows_path() -> None:
    """When ``which`` is None, an existing Windows install path is used."""
    target = mod.WINDOWS_VLC_PATHS[0]
    with patch(WHICH, return_value=None), patch(EXISTS, side_effect=lambda p: p == target):
        assert VlcLocator().vlc_binary() == target


def test_vlc_binary_raises_when_missing() -> None:
    """No ``which`` hit and no install path → PlaybackDependencyError."""
    with (
        patch(WHICH, return_value=None),
        patch(EXISTS, return_value=False),
        pytest.raises(PlaybackDependencyError, match="videolan.org"),
    ):
        VlcLocator().vlc_binary()


def test_vlc_binary_is_memoized() -> None:
    """``which`` is consulted only once across repeated calls."""
    locator = VlcLocator()
    with patch(WHICH, return_value="/usr/bin/vlc") as which:
        first = locator.vlc_binary()
        second = locator.vlc_binary()
    assert first == second == "/usr/bin/vlc"
    which.assert_called_once()


def test_ensure_libvlc_returns_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """A loadable fake ``vlc`` module is returned when Instance succeeds."""
    fake = _fake_vlc()
    monkeypatch.setitem(sys.modules, "vlc", fake)
    assert VlcLocator().ensure_libvlc() is fake


def test_ensure_libvlc_is_memoized(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Instance probe runs once; the module is cached afterwards."""
    calls: list[int] = []
    fake = _fake_vlc(instance=lambda *a, **k: calls.append(1))
    monkeypatch.setitem(sys.modules, "vlc", fake)
    locator = VlcLocator()
    locator.ensure_libvlc()
    locator.ensure_libvlc()
    assert len(calls) == 1


def test_ensure_libvlc_raises_on_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unimportable ``vlc`` module surfaces as PlaybackDependencyError."""
    monkeypatch.delitem(sys.modules, "vlc", raising=False)
    real_import = __import__

    def _import(name, *args, **kwargs):
        if name == "vlc":
            raise ImportError("no module named vlc")
        return real_import(name, *args, **kwargs)

    with (
        patch("builtins.__import__", side_effect=_import),
        pytest.raises(PlaybackDependencyError, match="videolan.org"),
    ):
        VlcLocator().ensure_libvlc()


def test_ensure_libvlc_raises_when_instance_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """libVLC failing to load (Instance raises) → PlaybackDependencyError."""
    def _boom(*args, **kwargs):
        raise OSError("libvlc.dll not found")

    monkeypatch.setitem(sys.modules, "vlc", _fake_vlc(instance=_boom))
    with pytest.raises(PlaybackDependencyError, match="videolan.org"):
        VlcLocator().ensure_libvlc()
