"""MetadataService: resolve a video's info dict / title without downloading.

Used for filename templating and pre-flight inspection (PLAN Phase 5.1, PRD §5).
It is intentionally thin — every network operation is delegated to
:class:`~ytdl.infra.ytdlp_client.YtDlpClient` (which routes through the
gatekeeper). No yt-dlp or network logic lives here.
"""

from __future__ import annotations

from typing import Any

from ytdl.infra.ytdlp_client import YtDlpClient


class MetadataService:
    """Resolve metadata for a YouTube URL via a :class:`YtDlpClient`.

    Args:
        client: The gatekeeper-routed yt-dlp client used for all resolution.
    """

    def __init__(self, client: YtDlpClient) -> None:
        self._client = client

    def info(
        self, url: str, opts: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Return the resolved info dict for ``url`` (no download).

        Args:
            url: The YouTube URL to resolve.
            opts: Optional yt-dlp options; ``None`` is passed through as ``{}``.

        Returns:
            The info dict produced by ``client.extract_info``.
        """
        return self._client.extract_info(url, opts or {})

    def title(self, url: str, opts: dict[str, Any] | None = None) -> str:
        """Return the video title, falling back safely when absent.

        Args:
            url: The YouTube URL to resolve.
            opts: Optional yt-dlp options forwarded to :meth:`info`.

        Returns:
            The ``title`` field if present and truthy; otherwise the video
            ``id`` if present; otherwise an empty string.
        """
        data = self.info(url, opts)
        title = data.get("title")
        if title:
            return title
        return data.get("id") or ""
