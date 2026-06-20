"""Domain exception hierarchy for the ytdl package."""


class YtdlError(Exception):
    """Base class for all ytdl errors."""


class ConfigVersionError(YtdlError):
    """Raised when a config file's version is not in SUPPORTED_CONFIG_VERSIONS."""


class ConfigNotFoundError(YtdlError):
    """Raised when a requested config file does not exist."""
