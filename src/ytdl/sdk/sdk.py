"""YoutubeDownloaderSDK: the SINGLE entry point for all business logic (Rule 1).

External layers (CLI, future GUI/REST) import only this class. It wires the full
stack from config (throttle pacing, JS runtime, persistent quota ledger), then
exposes :meth:`download` (fetch-once + union of post-processors, PRD §5) and
:meth:`probe_playlist` for interactive playlist selection.
"""

from __future__ import annotations

from typing import Any

from ytdl.infra.ytdlp_client import YtDlpClient
from ytdl.sdk.download_op import run_download as _run_download
from ytdl.sdk.probe import probe_playlist as _probe_playlist
from ytdl.sdk.wiring import (
    build_client,
    build_extra_opts,
    build_mixer,
    build_playlist_runner,
    build_sample_runner,
)
from ytdl.services.audio import AudioDownloader
from ytdl.services.base import BaseDownloader
from ytdl.services.metadata import MetadataService
from ytdl.services.subtitles import SubtitleDownloader
from ytdl.services.video import VideoDownloader
from ytdl.shared.config import ConfigManager
from ytdl.shared.version import __version__


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
        return _probe_playlist(self._client, self._base, url)

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
        return _run_download(
            self._client,
            self._base,
            self._video,
            self._audio,
            self._subs,
            self._config,
            url=url,
            video=video,
            audio=audio,
            subs=subs,
            output_dir=output_dir,
            name=name,
            resolution=resolution,
            sub_lang=sub_lang,
            no_playlist=no_playlist,
            playlist_items=playlist_items,
        )

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

    def sample_play(
        self,
        directory: str,
        *,
        play_for_sec: float | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        """Preview a folder by crossfading random mid-band samples (PRD-playlist §3).

        Builds segments via the :class:`Sampler`, checks the VLC dependency for the
        chosen ``mode`` (config ``playback.default_mode``, default option2), plays
        them, and loops while ``sample.loop``. Returns ``{mode, track_count, loop}``.
        """
        runner = build_sample_runner(self._config)
        return runner.run(directory, play_for_sec=play_for_sec, mode=mode)

    def play_playlist(self, yaml_path: str) -> dict[str, Any]:
        """Run a declarative YAML playlist (display/save/stream) (PRD-playlist §5).

        Delegates to a :class:`PlaylistRunner`; the SDK is passed as the
        rate-limited downloader for URL members. Returns the runner's report dict.
        """
        runner = build_playlist_runner(self._config, downloader=self)
        return runner.run(yaml_path)

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
