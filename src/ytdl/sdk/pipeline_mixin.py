"""Movie-pipeline SDK methods, mixed into :class:`YoutubeDownloaderSDK`.

Exposes the wizard-driven one-run pipeline through the single SDK entry point (Rule 1)
without growing ``sdk.py`` past 150 lines (Rule 8). The pipeline (``MoviePipeline``)
calls back into the SDK for analyze / search / download / build_movie / play_playlist.
"""

from __future__ import annotations

from typing import Any

from ytdl.services.pipeline.config import MovieConfig
from ytdl.services.pipeline.orchestrator import MoviePipeline
from ytdl.services.pipeline.prompter import Prompter
from ytdl.services.pipeline.wizard import MovieWizard


class PipelineMixin:
    """SDK methods for the idea+song → mixed-video pipeline."""

    def make_movie(self, config: MovieConfig, *, provider: Any = None) -> dict[str, Any]:
        """Run the full pipeline for a ready :class:`MovieConfig`; return its result."""
        return MoviePipeline(self, config, provider=provider).run()

    def run_movie_pipeline(self, config_path: str, *, provider: Any = None) -> dict[str, Any]:
        """Load a ``config.json`` and run the full pipeline; return its result."""
        return self.make_movie(MovieConfig.load(config_path), provider=provider)

    def plan_movie(self, config: MovieConfig) -> dict[str, Any]:
        """Run only STRUCTURE → write ``structure.json`` (lets the agent author the script)."""
        return MoviePipeline(self, config).plan()

    def movie_wizard(self, config_path: str, *, prompter: Prompter | None = None) -> str:
        """Run the interactive setup wizard and save the config; return its path."""
        wizard = MovieWizard(prompter or Prompter(), analyze_fn=self._wizard_song_summary)
        return wizard.run().save(config_path)

    def _wizard_song_summary(self, path: str) -> str:
        """One-line song summary (duration/BPM/bars) shown before the topic questions."""
        res = self.analyze_audio(path)  # type: ignore[attr-defined]
        meta, cut = res.get("metadata", {}), res.get("cut_points", {})
        return (f"  -> {meta.get('duration_seconds')}s, {meta.get('global_bpm')} BPM, "
                f"{len(cut.get('bars', []))} bars")
