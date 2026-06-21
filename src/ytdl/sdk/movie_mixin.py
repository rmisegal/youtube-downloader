"""Movie-agent SDK methods, mixed into :class:`YoutubeDownloaderSDK`.

Kept in a mixin (Rule 2 OOP, Rule 8 split-don't-condense) so the movie-maker agent
reaches every tool through the single SDK entry point (Rule 1) without growing
``sdk.py`` past 150 lines. ``search`` feeds the Video Content Matcher; ``build_movie``
turns the matcher's segments JSON into a playlist the mixer renders into one film.
"""

from __future__ import annotations

from typing import Any

from ytdl.services.movie.builder import build_movie_playlist, load_segments
from ytdl.services.movie.scaffold import candidates_to_segments, load_candidates, write_segments
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
        sync_target: str | None = None,
    ) -> str:
        """Build a playlist YAML from a matcher segments JSON; return its path."""
        return build_movie_playlist(
            load_segments(segments_path), video_dir, leading_audio=leading_audio,
            out_path=out_path, sync_target=sync_target,
        )

    def to_segments(self, candidates_path: str, out_path: str) -> str:
        """Scaffold an editable segments JSON from a ``--search`` candidates file."""
        return write_segments(candidates_to_segments(load_candidates(candidates_path)), out_path)

    def fetch_movie(self, segments_path: str, video_dir: str) -> dict[str, list[int]]:
        """Download each segment's video to ``seg_<n>.mp4`` with ``[N/total]`` progress."""
        segs = sorted(load_segments(segments_path), key=lambda s: s.get("sequence_number", 0))
        done: list[int] = []
        failed: list[int] = []
        for i, seg in enumerate(segs, start=1):
            n = seg.get("sequence_number", i)
            print(f"[fetch {i}/{len(segs)}] seg_{n}: {seg.get('video_url', '')}", flush=True)
            try:
                self.download(seg["video_url"], video=True, output_dir=video_dir,
                              name=f"seg_{n}", no_playlist=True)
                done.append(n)
            except Exception as exc:  # noqa: BLE001 - record + continue with the rest
                print(f"[fetch] seg_{n} FAILED: {exc}", flush=True)
                failed.append(n)
        print(f"[fetch] done: {len(done)}/{len(segs)} ok, failed={failed}", flush=True)
        return {"downloaded": done, "failed": failed}
