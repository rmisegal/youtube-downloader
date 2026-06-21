"""BaseDownloader: the single source of shared yt-dlp option logic.

Subclasses (Video/Audio/Subtitle) override :meth:`_mode_opts` to add their
format/post-processor specifics; everything common — ``outtmpl``,
``ffmpeg_location`` wiring, and the optional env-driven ``proxy``/``cookiefile``
values (PRD §6.4 / R44) — lives here so it is never duplicated (Rule 2).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ytdl.constants import (
    DEFAULT_NAME_TEMPLATE,
    ENV_COOKIES_FILE,
    ENV_PROXY,
    OUTTMPL_TEMPLATE,
)
from ytdl.infra.ffmpeg import FfmpegLocator
from ytdl.services.dl_progress import make_progress_hook
from ytdl.shared.config import ConfigManager


class BaseDownloader:
    """Shared yt-dlp option builder for all download modes (Template Method).

    Args:
        config: Source of all tunable values via ``config.get("a.b", default)``.
        ffmpeg: Locator for the bundled FFmpeg binary. Defaults to a fresh
            :class:`FfmpegLocator` (auto-resolved via ``imageio_ffmpeg``).
    """

    def __init__(
        self,
        config: ConfigManager,
        ffmpeg: FfmpegLocator | None = None,
        extra_opts: dict[str, Any] | None = None,
    ) -> None:
        self._config = config
        self._ffmpeg = ffmpeg if ffmpeg is not None else FfmpegLocator()
        # Cross-cutting yt-dlp opts injected by the SDK (throttle/ban-avoidance
        # pacing and the detected JS runtime). Applied to every download mode.
        self._extra_opts = dict(extra_opts or {})

    def build_base_opts(self, output_dir: str, name: str | None) -> dict[str, Any]:
        """Return yt-dlp options common to every download mode.

        Args:
            output_dir: Destination folder for produced files.
            name: Output base name (no extension). Falsy → title template.

        Returns:
            A new dict; optional ``proxy``/``cookiefile`` keys are present only
            when their env vars are set and non-empty (absent otherwise).
        """
        tail = OUTTMPL_TEMPLATE.format(name=name) if name else DEFAULT_NAME_TEMPLATE
        opts: dict[str, Any] = {
            "outtmpl": str(Path(output_dir) / tail),
            "ffmpeg_location": self._ffmpeg.exe(),
            "noprogress": True,  # replace yt-dlp's \r bar with a clean, log-friendly hook
            "progress_hooks": [make_progress_hook()],
        }
        # Throttle/JS-runtime opts injected by the SDK; base essentials win.
        for key, value in self._extra_opts.items():
            opts.setdefault(key, value)
        proxy = os.environ.get(ENV_PROXY)
        if proxy:
            opts["proxy"] = proxy
        cookies = os.environ.get(ENV_COOKIES_FILE)
        if cookies:
            opts["cookiefile"] = cookies
        return opts

    def _mode_opts(self, **kwargs: Any) -> dict[str, Any]:
        """Mode-specific options; overridden by subclasses (base adds none)."""
        return {}

    def build_opts(
        self,
        output_dir: str,
        name: str | None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Merge :meth:`build_base_opts` with subclass :meth:`_mode_opts`."""
        opts = self.build_base_opts(output_dir, name)
        opts.update(self._mode_opts(**kwargs))
        return opts
