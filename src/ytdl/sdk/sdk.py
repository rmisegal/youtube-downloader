"""YoutubeDownloaderSDK: the SINGLE entry point for all business logic (Rule 1).

External layers (CLI, future GUI/REST) import only this class. It wires the full
stack from config (throttle pacing, JS runtime, persistent quota ledger), then
exposes :meth:`download` (fetch-once + union of post-processors, PRD §5) and
:meth:`probe_playlist` for interactive playlist selection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ytdl.constants import MODE_AUDIO, MODE_SUBS, MODE_VIDEO
from ytdl.infra.ytdlp_client import YtDlpClient
from ytdl.sdk.compose import compose_opts
from ytdl.sdk.wiring import build_client, build_extra_opts, build_mixer
from ytdl.services.audio import AudioDownloader
from ytdl.services.base import BaseDownloader
from ytdl.services.metadata import MetadataService
from ytdl.services.subtitles import SubtitleDownloader
from ytdl.services.video import VideoDownloader
from ytdl.shared.config import ConfigManager
from ytdl.shared.version import __version__

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
        """Wire the stack from config; allow injection of a (mock) client/config for tests."""
        self._config = config or ConfigManager(file_name="setup.json")
        self._rate_config = rate_config or ConfigManager(file_name="rate_limits.json")
        self._client = client or build_client(self._rate_config)
        extra = build_extra_opts(self._config, self._rate_config)
        self._video = VideoDownloader(self._config)
        self._audio = AudioDownloader(self._config)
        self._subs = SubtitleDownloader(self._config)
        self._base = BaseDownloader(self._config, extra_opts=extra)
        self._metadata = MetadataService(self._client)

    def probe_playlist(self, url: str) -> dict[str, Any] | None:
        """Flat-resolve ``url``; return playlist info or ``None`` if it is a single video.

        Returns ``{"title", "count", "entries": [{"index", "id", "title"}, ...]}``.
        ``count`` is the total number of AVAILABLE items in the list.
        """
        opts = dict(self._base.build_base_opts(".", None))
        opts.update({"extract_flat": "in_playlist", "quiet": True, "no_warnings": True})
        info = self._client.extract_info(url, opts)
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
        no_playlist: bool = False,
        playlist_items: str | None = None,
    ) -> dict[str, Any]:
        """Download any combination of modes in a single fetch-once pass.

        Defaults to video-only when no mode flag is truthy (PRD §3.1). ``no_playlist``
        restricts a list URL to the single video; ``playlist_items`` (e.g. "1,3,5")
        selects specific entries. Returns a small dict describing what was produced.
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
        if no_playlist:
            merged["noplaylist"] = True
        if playlist_items:
            merged["playlist_items"] = playlist_items
        self._client.download(url, merged)

        modes = [
            mode
            for mode, on in ((MODE_VIDEO, video), (MODE_AUDIO, audio), (MODE_SUBS, subs))
            if on
        ]
        return {"url": url, "modes": modes, "output_dir": out_dir, "name": name}

    def mix_local_directory(
        self,
        directory: str,
        *,
        mode: str | None = None,
        selection: str | None = None,
        crossfade: int | None = None,
        source_mix_time: float | None = None,
        target_start_time: float | None = None,
    ) -> dict[str, Any]:
        """Run the VJ mixer over a local folder (PRD-mixer §3). Single entry point.

        Unspecified arguments fall back to the ``playback`` config block. The SDK is
        passed to the mixer as the rate-limited downloader for YouTube hot-injection.
        """
        mixer = build_mixer(self._config, downloader=self)
        return mixer.mix(
            directory,
            mode=mode,
            selection=selection,
            crossfade=crossfade,
            source_mix_time=source_mix_time,
            target_start_time=target_start_time,
        )

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
