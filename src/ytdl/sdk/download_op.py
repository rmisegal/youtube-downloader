"""Compose options and run a single fetch-once download pass (PRD §5).

Extracted from :class:`YoutubeDownloaderSDK` to keep ``sdk.py`` small. The SDK
method :meth:`YoutubeDownloaderSDK.download` resolves its defaults, then delegates
the option-composition + client call to :func:`run_download` here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ytdl.constants import MODE_AUDIO, MODE_SUBS, MODE_VIDEO
from ytdl.infra.ffprobe import ffmpeg_dir_with_probe
from ytdl.infra.ytdlp_client import YtDlpClient
from ytdl.sdk.compose import compose_opts
from ytdl.services.audio import AudioDownloader
from ytdl.services.base import BaseDownloader
from ytdl.services.subtitles import SubtitleDownloader
from ytdl.services.video import VideoDownloader
from ytdl.shared.config import ConfigManager

_OUTPUT_DIR_KEY = "paths.output_dir"
_RESOLUTION_KEY = "defaults.resolution"
_SUB_LANG_KEY = "defaults.sub_lang"
_DEFAULT_OUTPUT_DIR = "./downloads"


def _section_ranges(start: float, end: float) -> Any:
    """A yt-dlp ``download_ranges`` callable selecting one ``[start, end]`` window.

    Plain closure (no ``yt_dlp`` import here) — lets the movie pipeline fetch only the
    seconds it needs instead of a whole hours-long source video.
    """
    def ranges(_info: Any, _ydl: Any) -> list[dict[str, float]]:
        return [{"start_time": start, "end_time": end}]
    return ranges


def run_download(
    client: YtDlpClient,
    base: BaseDownloader,
    video_dl: VideoDownloader,
    audio_dl: AudioDownloader,
    subs_dl: SubtitleDownloader,
    config: ConfigManager,
    *,
    url: str,
    video: bool | None,
    audio: bool | None,
    subs: bool | None,
    output_dir: str | None,
    name: str | None,
    resolution: int | None,
    sub_lang: str | None,
    no_playlist: bool,
    playlist_items: str | None,
    sections: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Resolve defaults, compose merged opts, run one fetch, return a result dict.

    Defaults to video-only when no mode flag is truthy (PRD §3.1). ``no_playlist``
    restricts a list URL to the single video; ``playlist_items`` (e.g. "1,3,5")
    selects specific entries.
    """
    if not (video or audio or subs):
        video = True
    out_dir = output_dir or config.get(_OUTPUT_DIR_KEY, _DEFAULT_OUTPUT_DIR)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    if resolution is None:
        resolution = config.get(_RESOLUTION_KEY)
    if sub_lang is None:
        sub_lang = config.get(_SUB_LANG_KEY, "en")

    merged = compose_opts(
        base_opts=base.build_base_opts(out_dir, name),
        video=video_dl if video else None,
        audio=audio_dl if audio else None,
        subs=subs_dl if subs else None,
        resolution=resolution,
        sub_lang=sub_lang,
    )
    if no_playlist:
        merged["noplaylist"] = True
    if playlist_items:
        merged["playlist_items"] = playlist_items
    probe_dir = ffmpeg_dir_with_probe() if sections else None
    if sections and probe_dir:  # fetch only the window — needs ffmpeg+ffprobe (static-ffmpeg)
        merged["download_ranges"] = _section_ranges(*sections)
        merged["force_keyframes_at_cuts"] = True
        merged["ffmpeg_location"] = probe_dir
    # else: sections unavailable (offline) → fall back to a full download
    client.download(url, merged)

    modes = [
        mode
        for mode, on in ((MODE_VIDEO, video), (MODE_AUDIO, audio), (MODE_SUBS, subs))
        if on
    ]
    return {"url": url, "modes": modes, "output_dir": out_dir, "name": name}
