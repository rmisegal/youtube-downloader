"""VlcLocator: resolve the standalone VLC binary and the libVLC binding.

Two independent detection paths back the dual-engine architecture (PRD §4.3, §6):

* :meth:`vlc_binary` — locate the ``vlc`` executable for Option 1
  (FFmpeg → ``vlc -`` streaming server). Tries ``shutil.which`` first, then the
  common Windows install locations.
* :meth:`ensure_libvlc` — lazily ``import vlc`` (python-vlc) for Option 2 and
  confirm libVLC actually loads by constructing an ``Instance``.

Both raise :class:`PlaybackDependencyError` with an actionable message when the
required component is missing (CLI maps this to exit code 7).
"""

from __future__ import annotations

import os
import shutil
from types import ModuleType

from ytdl.shared.errors import PlaybackDependencyError

# Common Windows install locations probed when ``vlc`` is not on PATH.
WINDOWS_VLC_PATHS: tuple[str, ...] = (
    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
)

_INSTALL_HINT = "install it from https://www.videolan.org/"
_BINARY_MISSING = f"VLC Media Player not found — {_INSTALL_HINT}"
_LIBVLC_MISSING = f"libVLC (python-vlc) could not be loaded — {_INSTALL_HINT}"


class VlcLocator:
    """Resolves (and memoizes) the VLC binary and the libVLC binding."""

    def __init__(self) -> None:
        self._binary: str | None = None
        self._module: ModuleType | None = None

    def vlc_binary(self) -> str:
        """Return the standalone ``vlc`` executable path (Option 1).

        Resolution order: ``shutil.which("vlc")`` then the known Windows install
        paths. The result is cached after the first successful lookup.

        Raises:
            PlaybackDependencyError: if no ``vlc`` executable can be located.
        """
        if self._binary is None:
            self._binary = self._resolve_binary()
        return self._binary

    def ensure_libvlc(self) -> ModuleType:
        """Import python-vlc and confirm libVLC loads (Option 2).

        Lazily imports the ``vlc`` module and constructs an ``Instance`` to force
        libVLC to load, so a missing native library is detected here rather than
        deep inside playback. The module is cached after the first success.

        Raises:
            PlaybackDependencyError: if ``vlc`` cannot be imported or libVLC
                fails to initialise.
        """
        if self._module is None:
            self._module = self._resolve_libvlc()
        return self._module

    @staticmethod
    def _resolve_binary() -> str:
        """Locate the ``vlc`` executable or raise."""
        found = shutil.which("vlc")
        if found:
            return found
        for candidate in WINDOWS_VLC_PATHS:
            if os.path.exists(candidate):
                return candidate
        raise PlaybackDependencyError(_BINARY_MISSING)

    @staticmethod
    def _resolve_libvlc() -> ModuleType:
        """Import python-vlc and verify libVLC initialises, or raise."""
        try:
            import vlc
        except ImportError as exc:  # python-vlc not installed
            raise PlaybackDependencyError(_LIBVLC_MISSING) from exc
        try:
            vlc.Instance("--quiet")
        except Exception as exc:  # native libVLC failed to load
            raise PlaybackDependencyError(_LIBVLC_MISSING) from exc
        return vlc
