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

from ytdl.shared.gatekeeper import ApiGatekeeper


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
        """Perform the actual yt-dlp network operation (runs via gatekeeper)."""
        # Lazy import so the dependency loads only when needed and tests can
        # patch ``yt_dlp.YoutubeDL``. This is the sole reference to ``yt_dlp``.
        import yt_dlp

        return yt_dlp.YoutubeDL(opts).extract_info(url, download=download)
