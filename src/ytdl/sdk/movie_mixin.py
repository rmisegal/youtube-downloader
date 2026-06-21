"""Movie-agent SDK methods, mixed into :class:`YoutubeDownloaderSDK`.

Kept in a mixin (Rule 2 OOP, Rule 8 split-don't-condense) so the movie-maker agent
reaches every tool through the single SDK entry point (Rule 1) without growing
``sdk.py`` past 150 lines. ``search`` feeds the Video Content Matcher; ``build_movie``
turns the matcher's segments JSON into a playlist the mixer renders into one film.
"""

from __future__ import annotations

from typing import Any

from ytdl.services.movie.builder import build_movie_playlist, load_segments
from ytdl.services.movie.search import search_youtube


class MovieMixin:
    """SDK methods for the YouTube movie-maker agent (uses the SDK's client)."""

    _client: Any  # supplied by YoutubeDownloaderSDK.__init__ (the rate-limited client)

    def search(self, query: str, *, results: int = 8) -> list[dict[str, Any]]:
        """Search YouTube for candidate videos (title/url/duration) — matcher tool."""
        return search_youtube(self._client, query, results=results)

    def build_movie(
        self, segments_path: str, video_dir: str, *,
        leading_audio: str | None = None, out_path: str | None = None,
    ) -> str:
        """Build a playlist YAML from a matcher segments JSON; return its path."""
        return build_movie_playlist(
            load_segments(segments_path), video_dir,
            leading_audio=leading_audio, out_path=out_path,
        )
