"""VideoDownloader: mp4 download mode (best quality, optional height cap).

Subclasses :class:`~ytdl.services.base.BaseDownloader` and overrides only the
mode-specific hook :meth:`_mode_opts` (Rule 2 — no duplication). All shared
wiring (``outtmpl``, ``ffmpeg_location``, optional ``proxy``/``cookiefile``)
stays in the base class; this file adds nothing but the video format selector
and the mp4 merge target (PRD §3.2 / §5).
"""

from __future__ import annotations

from typing import Any

from ytdl.constants import (
    MERGE_OUTPUT_FORMAT,
    VIDEO_FORMAT_BEST,
    VIDEO_FORMAT_CAPPED,
)
from ytdl.services.base import BaseDownloader


class VideoDownloader(BaseDownloader):
    """Builds yt-dlp options for downloading a merged mp4 (video + audio).

    The base :meth:`~ytdl.services.base.BaseDownloader.build_opts` merges the
    result of :meth:`_mode_opts` on top of the shared base options, so callers
    invoke ``build_opts(output_dir, name, resolution=...)`` and receive the full
    option set.
    """

    def _mode_opts(self, **kwargs: Any) -> dict[str, Any]:
        """Return video-specific yt-dlp options.

        Args:
            **kwargs: Accepts ``resolution`` — an optional int max height
                (e.g. ``720``/``1080``). ``None`` (or absent) means best
                available quality with no height cap.

        Returns:
            A dict with the ``format`` selector and ``merge_output_format``.
        """
        resolution = kwargs.get("resolution")
        if resolution is None:
            fmt = VIDEO_FORMAT_BEST
        else:
            fmt = VIDEO_FORMAT_CAPPED.format(resolution=resolution)
        return {"format": fmt, "merge_output_format": MERGE_OUTPUT_FORMAT}
