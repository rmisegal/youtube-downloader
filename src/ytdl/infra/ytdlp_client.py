"""YtDlpClient: the *only* place ``yt_dlp.YoutubeDL`` is referenced.

A thin wrapper over ``yt_dlp.YoutubeDL`` whose every network operation is routed
through :class:`~ytdl.shared.gatekeeper.ApiGatekeeper`, satisfying the
architectural rule that all YouTube network calls go through the gatekeeper and
that ``yt_dlp`` is referenced nowhere else (PRD section 5; PLAN Phase 4.5).

No business logic about formats lives here — opts are built by the services and
passed straight through. ``yt_dlp`` is imported lazily inside the methods so the
import stays cheap and tests can patch ``yt_dlp.YoutubeDL``.
"""

from __future__ import annotations

from typing import Any

from ytdl.shared.errors import (
    InvalidUrlError,
    NetworkError,
    UnsupportedRequestError,
)
from ytdl.shared.gatekeeper import ApiGatekeeper

# Substrings (lower-cased) in a yt-dlp error message that indicate the URL itself
# is invalid/unavailable rather than a transient network problem.
_INVALID_URL_HINTS: tuple[str, ...] = (
    "is not a valid url",
    "unable to extract",
    "video unavailable",
    "private video",
    "does not exist",
    "incomplete youtube id",
    "not a valid url",
)


class YtDlpClient:
    """Gatekeeper-routed wrapper around ``yt_dlp.YoutubeDL``."""

    def __init__(self, gatekeeper: ApiGatekeeper) -> None:
        """Build a client.

        Args:
            gatekeeper: The single choke point through which every yt-dlp
                network operation is executed (rate-limited, retried, logged).
        """
        self._gatekeeper = gatekeeper

    def extract_info(self, url: str, opts: dict[str, Any]) -> dict[str, Any]:
        """Resolve metadata for ``url`` without downloading.

        Builds ``yt_dlp.YoutubeDL(opts)`` and calls
        ``.extract_info(url, download=False)`` through the gatekeeper.

        Args:
            url: The YouTube URL to resolve.
            opts: yt-dlp options dict (built by the caller/services).

        Returns:
            The info dict yt-dlp produced.
        """
        return self._gatekeeper.execute(self._extract, url, opts, False)

    def download(self, url: str, opts: dict[str, Any]) -> dict[str, Any]:
        """Resolve and download ``url`` in a single pass.

        Builds ``yt_dlp.YoutubeDL(opts)`` and calls
        ``.extract_info(url, download=True)`` through the gatekeeper. Doing both
        in one pass satisfies PRD section 5 "fetch once" when ``opts`` carry the
        union of post-processors.

        Args:
            url: The YouTube URL to download.
            opts: yt-dlp options dict (built by the caller/services).

        Returns:
            Whatever info/result yt-dlp returns from the download pass.
        """
        return self._gatekeeper.execute(self._extract, url, opts, True)

    @staticmethod
    def _extract(url: str, opts: dict[str, Any], download: bool) -> dict[str, Any]:
        """Perform the actual yt-dlp network operation (runs via gatekeeper).

        Catches yt-dlp's own exceptions and re-raises them as domain exceptions
        so ``yt_dlp`` stays confined to this infra module and callers (CLI/SDK)
        get clean, stable types to handle.
        """
        # Lazy import so the dependency loads only when needed and tests can
        # patch ``yt_dlp.YoutubeDL``. This is the sole reference to ``yt_dlp``.
        import yt_dlp
        from yt_dlp.utils import DownloadError, ExtractorError, UnsupportedError

        try:
            return yt_dlp.YoutubeDL(opts).extract_info(url, download=download)
        except UnsupportedError as exc:
            raise UnsupportedRequestError(str(exc)) from exc
        except (DownloadError, ExtractorError) as exc:
            raise _translate_download_error(exc) from exc


def _translate_download_error(exc: Exception) -> Exception:
    """Map a yt-dlp DownloadError/ExtractorError to a domain exception."""
    message = str(exc)
    lowered = message.lower()
    if any(hint in lowered for hint in _INVALID_URL_HINTS):
        return InvalidUrlError(message)
    return NetworkError(message)
