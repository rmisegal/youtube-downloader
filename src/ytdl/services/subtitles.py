"""SubtitleDownloader: fetch subtitles as ``.srt`` via yt-dlp + FFmpeg.

Subclasses :class:`BaseDownloader` and overrides only the ``_mode_opts`` hook
(Rule 2 — no duplication); ``outtmpl``/``ffmpeg_location`` wiring stays in the
base. Both manual and auto-generated subtitles are requested (PRD §3.2 / §5),
and an ``FFmpegSubtitlesConvertor`` post-processor guarantees ``.srt`` output
even when only auto-captions exist. The language defaults to the configured
``defaults.sub_lang`` and is never hardcoded (Rule 11).
"""

from __future__ import annotations

from typing import Any

from ytdl.services.base import BaseDownloader

# yt-dlp post-processor key for FFmpeg subtitle conversion (true constant).
_CONVERT_SUBS_KEY = "FFmpegSubtitlesConvertor"
# Target subtitle container/format for both the option and the converter.
_SUB_FORMAT = "srt"
# Config key + last-resort fallback (mirrors config/setup.json "defaults").
_CFG_SUB_LANG = "defaults.sub_lang"
_DEFAULT_SUB_LANG = "en"


class SubtitleDownloader(BaseDownloader):
    """Builds yt-dlp options that download subtitles and convert them to srt."""

    def _mode_opts(self, **kwargs: Any) -> dict[str, Any]:
        """Return subtitle options for the requested (or configured) language.

        The language is taken from the ``sub_lang`` kwarg when provided,
        otherwise from the ``defaults.sub_lang`` config value (default ``"en"``).
        Both manual and auto-generated subtitles are requested so a track is
        always available; the ``FFmpegSubtitlesConvertor`` post-processor then
        guarantees ``.srt`` output even from auto-captions.
        """
        sub_lang = kwargs.get("sub_lang")
        if not sub_lang:
            sub_lang = self._config.get(_CFG_SUB_LANG, _DEFAULT_SUB_LANG)
        return {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [sub_lang],
            "subtitlesformat": _SUB_FORMAT,
            "postprocessors": [
                {"key": _CONVERT_SUBS_KEY, "format": _SUB_FORMAT},
            ],
        }
