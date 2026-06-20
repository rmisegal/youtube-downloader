"""Compose a single merged yt-dlp options dict from the selected modes.

This is the "fetch-once + union of post-processors" logic from PRD §5: the SDK
selects which downloaders are active, then merges their option dicts over the
shared base opts so the video is resolved/downloaded in exactly one pass. Plain
keys are merged; ``postprocessors`` lists are CONCATENATED across modes.
"""

from __future__ import annotations

from typing import Any

from ytdl.services.audio import AudioDownloader
from ytdl.services.subtitles import SubtitleDownloader
from ytdl.services.video import VideoDownloader

# yt-dlp opt key that keeps the merged video file when audio is also extracted.
_KEEP_VIDEO = "keepvideo"
_POSTPROCESSORS = "postprocessors"


def _merge(base: dict[str, Any], extra: dict[str, Any]) -> None:
    """Merge ``extra`` into ``base`` in place, concatenating post-processors."""
    for key, value in extra.items():
        if key == _POSTPROCESSORS:
            base.setdefault(_POSTPROCESSORS, [])
            base[_POSTPROCESSORS].extend(value)
        else:
            base[key] = value


def compose_opts(
    *,
    base_opts: dict[str, Any],
    video: VideoDownloader | None,
    audio: AudioDownloader | None,
    subs: SubtitleDownloader | None,
    resolution: Any,
    sub_lang: Any,
) -> dict[str, Any]:
    """Return one merged opts dict layering each selected mode over ``base_opts``.

    Args:
        base_opts: Shared base options (outtmpl, ffmpeg_location, ...).
        video: VideoDownloader when video mode is selected, else ``None``.
        audio: AudioDownloader when audio mode is selected, else ``None``.
        subs: SubtitleDownloader when subtitle mode is selected, else ``None``.
        resolution: Max video height (or ``None`` for best) for the video mode.
        sub_lang: Subtitle language code for the subtitle mode.

    Returns:
        A new dict with merged plain keys and a concatenated ``postprocessors``
        list. When BOTH video and audio are selected, ``keepvideo`` is set True
        so FFmpegExtractAudio does not delete the merged mp4.
    """
    merged: dict[str, Any] = dict(base_opts)
    if video is not None:
        _merge(merged, video._mode_opts(resolution=resolution))
    if audio is not None:
        _merge(merged, audio._mode_opts())
    if subs is not None:
        _merge(merged, subs._mode_opts(sub_lang=sub_lang))
    if video is not None and audio is not None:
        # Audio extraction would otherwise remove the video; keep both files.
        merged[_KEEP_VIDEO] = True
    return merged
