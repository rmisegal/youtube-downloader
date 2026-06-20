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

# --- Video mixer / VJ playback (PRD-mixer §2/§4) ---
# Local media formats the mixer will index from a folder (config mirrors this).
SUPPORTED_VIDEO_FORMATS: tuple[str, ...] = (".mp4", ".mkv", ".mov", ".avi")
# Playback engine identifiers.
PLAYBACK_OPTION1: str = "option1"  # FFmpeg xfade/acrossfade -> VLC stdin (true crossfade)
PLAYBACK_OPTION2: str = "option2"  # dual-libVLC gapless switching + audio crossfade
PLAYBACK_MODES: tuple[str, ...] = (PLAYBACK_OPTION1, PLAYBACK_OPTION2)
# Track selection strategies.
SELECTION_RANDOM: str = "random"
SELECTION_MANUAL: str = "manual"
SELECTION_MODES: tuple[str, ...] = (SELECTION_RANDOM, SELECTION_MANUAL)

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

# --- Sampler / playlist names (PRD-playlist §2-§6) ---
# Numeric sampler/render tunables live in config (sample.*/render.*); only stable
# string identifiers belong here.
# Transition / mix effect names.
EFFECT_FADE: str = "fade"
# Playlist member kinds (metadata member ``type``).
MEMBER_VIDEO: str = "video"
MEMBER_IMAGE: str = "image"
MEMBER_KINDS: tuple[str, ...] = (MEMBER_VIDEO, MEMBER_IMAGE)
# Still-image source formats indexed for the mixer/playlist.
SUPPORTED_IMAGE_FORMATS: tuple[str, ...] = (
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif",
)
# Per-image transition/animation names (FFmpeg zoompan + fade); ``random`` picks one.
TRANSITION_RANDOM: str = "random"
TRANSITION_FADE: str = "fade"
TRANSITION_ZOOMIN: str = "zoomin"
TRANSITION_ZOOMOUT: str = "zoomout"
TRANSITION_PANLEFT: str = "panleft"
TRANSITION_PANRIGHT: str = "panright"
TRANSITION_PANUP: str = "panup"
TRANSITION_PANDOWN: str = "pandown"
# Concrete transitions ``random`` may resolve to (excludes ``random`` itself).
IMAGE_TRANSITIONS: tuple[str, ...] = (
    TRANSITION_FADE,
    TRANSITION_ZOOMIN,
    TRANSITION_ZOOMOUT,
    TRANSITION_PANLEFT,
    TRANSITION_PANRIGHT,
    TRANSITION_PANUP,
    TRANSITION_PANDOWN,
)
# Playlist output-mode names (metadata.output toggles).
OUTPUT_DISPLAY: str = "display"
OUTPUT_SAVE: str = "save"
OUTPUT_STREAM: str = "stream"
OUTPUT_MODES: tuple[str, ...] = (OUTPUT_DISPLAY, OUTPUT_SAVE, OUTPUT_STREAM)
# Mix stream names (metadata.mix toggles).
MIX_VIDEO: str = "video"
MIX_AUDIO: str = "audio"
MIX_SUBTITLE: str = "subtitle"
MIX_STREAMS: tuple[str, ...] = (MIX_VIDEO, MIX_AUDIO, MIX_SUBTITLE)
# Leading-track kinds (metadata.leading.kind).
LEADING_NONE: str = "none"
LEADING_VIDEO: str = "video"
LEADING_AUDIO: str = "audio"
LEADING_KINDS: tuple[str, ...] = (LEADING_NONE, LEADING_VIDEO, LEADING_AUDIO)

# --- Environment variable names for optional, user-supplied secrets ---
ENV_PROXY: str = "YTDL_PROXY"
ENV_COOKIES_FILE: str = "YTDL_COOKIES_FILE"
