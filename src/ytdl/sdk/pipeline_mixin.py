"""Movie-pipeline SDK methods, mixed into :class:`YoutubeDownloaderSDK`.

Exposes the wizard-driven one-run pipeline through the single SDK entry point (Rule 1)
without growing ``sdk.py`` past 150 lines (Rule 8). The pipeline (``MoviePipeline``)
calls back into the SDK for analyze / search / download / build_movie / play_playlist.
"""

from __future__ import annotations

from typing import Any

from ytdl.services.pipeline.config import MovieConfig
from ytdl.services.pipeline.orchestrator import MoviePipeline


class PipelineMixin:
    """SDK methods for the idea+song → mixed-video pipeline."""

    def make_movie(self, config: MovieConfig, *, provider: Any = None) -> dict[str, Any]:
        """Run the full pipeline for a ready :class:`MovieConfig`; return its result."""
        return MoviePipeline(self, config, provider=provider).run()

    def run_movie_pipeline(self, config_path: str, *, provider: Any = None) -> dict[str, Any]:
        """Load a ``config.json`` and run the full pipeline; return its result."""
        return self.make_movie(MovieConfig.load(config_path), provider=provider)
