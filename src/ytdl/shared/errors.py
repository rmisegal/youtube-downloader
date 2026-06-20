"""Domain exception hierarchy for the ytdl package."""


class YtdlError(Exception):
    """Base class for all ytdl errors."""


class ConfigVersionError(YtdlError):
    """Raised when a config file's version is not in SUPPORTED_CONFIG_VERSIONS."""


class ConfigNotFoundError(YtdlError):
    """Raised when a requested config file does not exist."""


class InvalidUrlError(YtdlError):
    """Raised when the supplied URL is invalid or the video is unavailable."""


class NetworkError(YtdlError):
    """Raised when a network/download failure persists after retries."""


class UnsupportedRequestError(YtdlError):
    """Raised when yt-dlp cannot handle the requested URL/extractor."""


class RateLimitExceededError(YtdlError):
    """Raised when a configured request quota (minute/hour/day/month) is hit,
    or when YouTube returns HTTP 429. Stopping here protects the account from
    being throttled/blocked by YouTube."""


class PlaybackDependencyError(YtdlError):
    """Raised when the video mixer cannot find a required external dependency
    (VLC Media Player binary for Option 1, or libVLC/python-vlc for Option 2)."""
