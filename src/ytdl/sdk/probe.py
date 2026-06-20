"""Flat-resolve a URL into playlist info for interactive selection (PRD §3).

Extracted from :class:`YoutubeDownloaderSDK` to keep ``sdk.py`` small. The SDK
method :meth:`YoutubeDownloaderSDK.probe_playlist` is a thin delegate to
:func:`probe_playlist` here, passing its wired client and base downloader.
"""

from __future__ import annotations

from typing import Any

from ytdl.infra.ytdlp_client import YtDlpClient
from ytdl.services.base import BaseDownloader


def probe_playlist(
    client: YtDlpClient,
    base: BaseDownloader,
    url: str,
) -> dict[str, Any] | None:
    """Flat-resolve ``url``; return playlist info or ``None`` for a single video.

    Returns ``{"title", "count", "entries": [{"index", "id", "title"}, ...]}``.
    ``count`` is the total number of AVAILABLE items in the list.
    """
    opts = dict(base.build_base_opts(".", None))
    opts.update({"extract_flat": "in_playlist", "quiet": True, "no_warnings": True})
    info = client.extract_info(url, opts)
    entries = list(info.get("entries") or [])
    if info.get("_type") != "playlist" and not entries:
        return None
    items = [
        {"index": i, "id": e.get("id"), "title": e.get("title") or e.get("id") or f"item {i}"}
        for i, e in enumerate(entries, start=1)
    ]
    return {
        "title": info.get("title"),
        "count": info.get("playlist_count") or len(items),
        "entries": items,
    }
