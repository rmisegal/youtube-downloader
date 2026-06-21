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
MEMBER_TITLE: str = "title"  # text card: random words over a background image (drawtext)
MEMBER_KINDS: tuple[str, ...] = (MEMBER_VIDEO, MEMBER_IMAGE, MEMBER_TITLE)
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
# Deliberate fade-THROUGH-BLACK — reserved for dramatic moments (section changes),
# NOT a per-clip edge fade. Other transitions are clean (no black) so contiguous
# slides flow without a black gap between them.
TRANSITION_FADEBLACK: str = "fadeblack"
# Beat-reactive effects (PRD-beatsync): pulse/shake/bounce/flash at the music BPM.
TRANSITION_PULSE: str = "pulse"  # heartbeat zoom throb on every beat
TRANSITION_SHAKE: str = "shake"  # fast positional jitter (build-ups)
TRANSITION_BOUNCE: str = "bounce"  # vertical bob on the beat
TRANSITION_FLASH: str = "flash"  # brightness pulse on the beat
BEAT_TRANSITIONS: tuple[str, ...] = (
    TRANSITION_PULSE,
    TRANSITION_SHAKE,
    TRANSITION_BOUNCE,
    TRANSITION_FLASH,
)
# Concrete STATIC transitions ``random`` may resolve to (no music needed).
IMAGE_TRANSITIONS: tuple[str, ...] = (
    TRANSITION_FADE,
    TRANSITION_ZOOMIN,
    TRANSITION_ZOOMOUT,
    TRANSITION_PANLEFT,
    TRANSITION_PANRIGHT,
    TRANSITION_PANUP,
    TRANSITION_PANDOWN,
)
# Every recognised transition (static + beat-reactive + the deliberate fade-to-black).
ALL_TRANSITIONS: tuple[str, ...] = IMAGE_TRANSITIONS + BEAT_TRANSITIONS + (TRANSITION_FADEBLACK,)
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

# --- Beat-sync audio analysis (PRD-beatsync) ---
# Analysis tiers (cut-point resolutions).
TIER_BEAT: str = "beat"
TIER_BAR: str = "bar"
TIER_PHRASE: str = "phrase"
TIER_SECTION: str = "section"
ANALYSIS_TIERS: tuple[str, ...] = (TIER_BEAT, TIER_BAR, TIER_PHRASE, TIER_SECTION)
# Heuristic section labels.
SECTION_INTRO: str = "Intro"
SECTION_VERSE: str = "Verse"
SECTION_BUILD: str = "Build-up"
SECTION_CHORUS: str = "Chorus"
SECTION_OUTRO: str = "Outro"
# Playlist sync modes (metadata.sync.mode): ``auto`` = context-aware planner.
SYNC_AUTO: str = "auto"
SYNC_MODES: tuple[str, ...] = (SYNC_AUTO, TIER_BEAT, TIER_BAR, TIER_PHRASE, TIER_SECTION)
# Audio formats the analyzer accepts.
SUPPORTED_AUDIO_FORMATS: tuple[str, ...] = (".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg")

# --- Environment variable names for optional, user-supplied secrets ---
ENV_PROXY: str = "YTDL_PROXY"
ENV_COOKIES_FILE: str = "YTDL_COOKIES_FILE"
