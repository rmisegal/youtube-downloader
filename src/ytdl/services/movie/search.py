"""YouTube search for the Video Content Matcher skill (yt-dlp ``ytsearch``).

Returns candidate videos with their durations so the matcher can validate each
topic against a minimum-duration requirement. Goes through the same rate-limited
:class:`YtDlpClient` as every other YouTube call (no direct yt-dlp here).
"""

from __future__ import annotations

from typing import Any


def _entry(e: dict[str, Any]) -> dict[str, Any]:
    url = e.get("url") or e.get("webpage_url") or (f"https://youtu.be/{e['id']}" if e.get("id") else "")
    return {
        "video_title": e.get("title", ""),
        "video_url": url,
        "duration_seconds": int(e.get("duration") or 0),
        "channel": e.get("channel") or e.get("uploader", ""),
    }


def search_youtube(client: Any, query: str, *, results: int = 8) -> list[dict[str, Any]]:
    """Search YouTube for ``query``; return up to ``results`` ``{title,url,duration}`` dicts."""
    info = client.extract_info(
        f"ytsearch{max(1, results)}:{query}",
        {"extract_flat": True, "quiet": True, "skip_download": True},
    )
    return [_entry(e) for e in (info.get("entries") or []) if e]
