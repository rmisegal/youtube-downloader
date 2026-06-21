"""Aggregator for the SDK mixins — keeps ``sdk.py``'s import block within 150 lines.

The SDK composes feature mixins (movie-agent tools + the movie pipeline) so each
feature area lives in its own ≤150-line file (Rule 8) while still reaching the user
through the single :class:`YoutubeDownloaderSDK` entry point (Rule 1).
"""

from ytdl.sdk.movie_mixin import MovieMixin
from ytdl.sdk.pipeline_mixin import PipelineMixin

__all__ = ["MovieMixin", "PipelineMixin"]
