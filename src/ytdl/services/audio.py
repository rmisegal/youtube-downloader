"""AudioDownloader: extract audio via yt-dlp's FFmpeg post-processor.

Subclasses :class:`BaseDownloader` and overrides only the ``_mode_opts`` hook
(Rule 2 — no duplication); ``outtmpl``/``ffmpeg_location`` wiring stays in the
base. The ``preferredcodec``/``preferredquality`` come from the
:class:`ConfigManager` (``audio.codec`` / ``audio.quality``), never hardcoded in
the option dict (PRD §3.2 / §5; Rule 11).
"""

from __future__ import annotations

from typing import Any

from ytdl.services.base import BaseDownloader

# yt-dlp post-processor key for FFmpeg audio extraction (true constant).
_EXTRACT_AUDIO_KEY = "FFmpegExtractAudio"
# Config keys + last-resort fallbacks (mirrors config/setup.json "audio").
_CFG_CODEC = "audio.codec"
_CFG_QUALITY = "audio.quality"
_DEFAULT_CODEC = "mp3"
_DEFAULT_QUALITY = "192"


class AudioDownloader(BaseDownloader):
    """Builds yt-dlp options that extract the audio track to a chosen codec."""

    def _mode_opts(self, **kwargs: Any) -> dict[str, Any]:
        """Return the ``FFmpegExtractAudio`` post-processor, config-driven.

        ``preferredcodec`` and ``preferredquality`` are read from the
        ``ConfigManager`` so changing the config changes the produced opts.
        """
        codec = self._config.get(_CFG_CODEC, _DEFAULT_CODEC)
        quality = self._config.get(_CFG_QUALITY, _DEFAULT_QUALITY)
        return {
            "postprocessors": [
                {
                    "key": _EXTRACT_AUDIO_KEY,
                    "preferredcodec": codec,
                    "preferredquality": quality,
                }
            ]
        }
