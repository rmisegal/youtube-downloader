"""YoutubeDownloaderSDK: the SINGLE entry point for all business logic (Rule 1).

External layers (CLI, future GUI/REST) import only this class. It wires the full
stack from config, then exposes :meth:`download` which resolves the requested
modes, composes ONE merged yt-dlp opts dict (fetch-once + union of
post-processors, PRD §5), and performs a single download pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ytdl.constants import MODE_AUDIO, MODE_SUBS, MODE_VIDEO
from ytdl.infra.ytdlp_client import YtDlpClient
from ytdl.sdk.compose import compose_opts
from ytdl.services.audio import AudioDownloader
from ytdl.services.base import BaseDownloader
from ytdl.services.metadata import MetadataService
from ytdl.services.subtitles import SubtitleDownloader
from ytdl.services.video import VideoDownloader
from ytdl.shared.config import ConfigManager
from ytdl.shared.gatekeeper import ApiGatekeeper
from ytdl.shared.queue import DownloadQueue
from ytdl.shared.rate_limit import RateLimiter
from ytdl.shared.version import __version__

_YT_LIMITS_KEY = "rate_limits.services.youtube"
_OUTPUT_DIR_KEY = "paths.output_dir"
_RESOLUTION_KEY = "defaults.resolution"
_SUB_LANG_KEY = "defaults.sub_lang"
_DEFAULT_OUTPUT_DIR = "./downloads"


class YoutubeDownloaderSDK:
    """Single public surface for downloading video/audio/subtitles."""

    def __init__(
        self,
        client: YtDlpClient | None = None,
        config: ConfigManager | None = None,
        rate_config: ConfigManager | None = None,
    ) -> None:
        """Wire the stack from config; allow injection for tests.

        Args:
            client: Optional pre-built (mock) :class:`YtDlpClient`. When ``None``
                the full gatekeeper/rate-limit/queue stack is built from config.
            config: ``setup.json`` manager (defaults to repo ``config/``).
            rate_config: ``rate_limits.json`` manager (defaults to repo config).
        """
        self._config = config or ConfigManager(file_name="setup.json")
        self._rate_config = rate_config or ConfigManager(file_name="rate_limits.json")
        self._client = client or self._build_client()
        self._video = VideoDownloader(self._config)
        self._audio = AudioDownloader(self._config)
        self._subs = SubtitleDownloader(self._config)
        self._base = BaseDownloader(self._config)
        self._metadata = MetadataService(self._client)

    def _build_client(self) -> YtDlpClient:
        """Assemble RateLimiter + DownloadQueue + gatekeeper + client."""
        limits = self._rate_config.get(_YT_LIMITS_KEY, {})
        limiter = RateLimiter(limits)
        queue = DownloadQueue(self._rate_config)
        gatekeeper = ApiGatekeeper(
            limiter,
            queue,
            max_retries=limits.get("max_retries", 3),
            retry_after_seconds=limits.get("retry_after_seconds", 30),
        )
        return YtDlpClient(gatekeeper)

    def download(
        self,
        url: str,
        *,
        video: bool | None = None,
        audio: bool | None = None,
        subs: bool | None = None,
        output_dir: str | None = None,
        name: str | None = None,
        resolution: int | None = None,
        sub_lang: str | None = None,
    ) -> dict[str, Any]:
        """Download any combination of modes in a single fetch-once pass.

        Defaults to video-only when no mode flag is truthy (PRD §3.1). All three
        modes are independent toggles and fully combinable. Returns a small dict
        describing what was produced.
        """
        if not (video or audio or subs):
            video = True
        out_dir = output_dir or self._config.get(_OUTPUT_DIR_KEY, _DEFAULT_OUTPUT_DIR)
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        if resolution is None:
            resolution = self._config.get(_RESOLUTION_KEY)
        if sub_lang is None:
            sub_lang = self._config.get(_SUB_LANG_KEY, "en")

        merged = compose_opts(
            base_opts=self._base.build_base_opts(out_dir, name),
            video=self._video if video else None,
            audio=self._audio if audio else None,
            subs=self._subs if subs else None,
            resolution=resolution,
            sub_lang=sub_lang,
        )
        self._client.download(url, merged)

        modes = [
            mode
            for mode, on in ((MODE_VIDEO, video), (MODE_AUDIO, audio), (MODE_SUBS, subs))
            if on
        ]
        return {"url": url, "modes": modes, "output_dir": out_dir, "name": name}

    def download_video(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """Convenience: download video only (delegates to :meth:`download`)."""
        return self.download(url, video=True, **kwargs)

    def download_audio(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """Convenience: extract audio only (delegates to :meth:`download`)."""
        return self.download(url, audio=True, **kwargs)

    def download_subtitles(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """Convenience: download subtitles only (delegates to :meth:`download`)."""
        return self.download(url, subs=True, **kwargs)

    @staticmethod
    def version() -> str:
        """Return the application code version (PRD §6.5; CLI ``--version``)."""
        return __version__
