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
