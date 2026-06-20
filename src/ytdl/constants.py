"""True constants and last-resort fallbacks for ytdl.

Only immutable values live here. Every tunable belongs in ``config/*.json`` and is
read via :class:`ytdl.shared.config.ConfigManager`.
"""

from __future__ import annotations

# --- Download mode names (stable identifiers used across layers) ---
MODE_VIDEO: str = "video"
MODE_AUDIO: str = "audio"
MODE_SUBS: str = "subs"
ALL_MODES: tuple[str, ...] = (MODE_VIDEO, MODE_AUDIO, MODE_SUBS)

# --- Output file extensions ---
EXT_VIDEO: str = "mp4"
EXT_AUDIO: str = "mp3"
EXT_SUBTITLE: str = "srt"
SUPPORTED_SUBTITLE_EXTS: tuple[str, ...] = ("srt", "vtt", "ass")
SUPPORTED_OUTPUT_EXTS: tuple[str, ...] = (EXT_VIDEO, EXT_AUDIO, EXT_SUBTITLE)

# --- yt-dlp format selectors (templates filled at runtime) ---
# Best video+audio merged; cap height when a resolution is requested.
VIDEO_FORMAT_BEST: str = "bv*+ba/b"
VIDEO_FORMAT_CAPPED: str = "bv*[height<={resolution}]+ba/b"

# --- yt-dlp output template (filled with output_dir + base name) ---
# yt-dlp substitutes %(ext)s with the produced file extension.
OUTTMPL_TEMPLATE: str = "{name}.%(ext)s"
DEFAULT_NAME_TEMPLATE: str = "%(title)s"
MERGE_OUTPUT_FORMAT: str = "mp4"

# --- yt-dlp post-processor keys ---
PP_EXTRACT_AUDIO: str = "FFmpegExtractAudio"
PP_CONVERT_SUBS: str = "FFmpegSubtitlesConvertor"

# --- Environment variable names for optional, user-supplied secrets ---
ENV_PROXY: str = "YTDL_PROXY"
ENV_COOKIES_FILE: str = "YTDL_COOKIES_FILE"
