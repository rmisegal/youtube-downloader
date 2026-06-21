"""``MoviePipeline`` — the Orchestrator Agent (in software) for PRD-mix-video-pipeline.

Sequences STRUCTURE → SCRIPT → MATCH → FETCH → BUILD → RENDER → REPORT, persisting each
stage's artifact to the BUILD folder so a re-run resumes. Every external call is
delegated to the SDK (Rule 1: analyze / search / download / build_movie / play_playlist);
the LLM SCRIPT stage uses an injected (or factory-built) provider, and the agent path
may pre-write ``script.json``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ytdl.services.llm.factory import build_provider
from ytdl.services.movie.builder import to_seconds
from ytdl.services.pipeline.fetch_stage import fetch_segments
from ytdl.services.pipeline.match_stage import match_scenes
from ytdl.services.pipeline.report import write_report
from ytdl.services.pipeline.script_stage import generate_script
from ytdl.services.pipeline.state import StageState
from ytdl.services.pipeline.structure import build_scenario_grid

_SEARCH_RESULTS = 6


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


class MoviePipeline:
    """Run the full idea+song → mixed-video pipeline for one ``MovieConfig``."""

    def __init__(self, sdk: Any, config: Any, *, provider: Any = None) -> None:
        self._sdk = sdk
        self._cfg = config
        self._provider = provider

    def _build_dir(self) -> Path:
        slug = re.sub(r"\W+", "-", (self._cfg.topic or self._cfg.idea or "movie")).strip("-").lower()
        base = self._cfg.output_dir or str(Path.home() / "movies")
        return Path(base) / (slug or "movie")

    def _structure(self, build: Path, state: StageState) -> list[dict[str, Any]]:
        path = build / "structure.json"
        if state.is_done("structure") and path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        if self._cfg.has_leading:
            analysis = self._sdk.analyze_audio(self._cfg.leading)
        else:
            total = self._cfg.scene_target * self._cfg.scene_seconds
            analysis = {"metadata": {"duration_seconds": total}, "cut_points": {}}
        grid = build_scenario_grid(analysis, self._cfg.scene_target)
        _write(path, grid)
        state.mark_done("structure", scenes=len(grid))
        return grid

    def _script(self, build: Path, grid: list[dict[str, Any]]) -> list[dict[str, Any]]:
        path = build / "script.json"
        if path.exists():  # resume, or the agent pre-wrote the script
            return json.loads(path.read_text(encoding="utf-8"))
        provider = self._provider or build_provider(self._cfg.llm_vendor, self._cfg.llm_auth)
        script = generate_script(provider, self._cfg, grid)
        _write(path, script)
        return script

    def _match(self, build: Path, script: list[dict[str, Any]]) -> list[dict[str, Any]]:
        segments = match_scenes(
            lambda q, n: self._sdk.search(q, results=n), script, str(build), results=_SEARCH_RESULTS,
        )
        _write(build / "segments.json", segments)
        return segments

    def _fetch(self, videos: Path, segments: list[dict[str, Any]]) -> tuple[list[int], list[int]]:
        def download(url: str, name: str, seg: dict[str, Any]) -> Any:
            start = to_seconds(seg.get("start_time", 0))
            dur = float(seg.get("duration_seconds", 6) or 6)
            return self._sdk.download(url, video=True, output_dir=str(videos), name=name,
                                      no_playlist=True, resolution=self._cfg.download_resolution,
                                      sections=(start, start + dur + 1.0))
        return fetch_segments(download, segments, str(videos))

    def _build_playlist(self, build: Path, videos: Path, segments: list[dict[str, Any]]) -> str:
        # Clips were fetched as their in-point window → the file starts at 0, so build
        # from start 0 (not the original source timestamp).
        trimmed = [{**s, "start_time": "00:00:00"} for s in segments]
        _write(build / "build_segments.json", trimmed)
        return self._sdk.build_movie(
            str(build / "build_segments.json"), str(videos),
            leading_audio=self._cfg.leading or None,
            sync_target=self._cfg.sync_target if self._cfg.has_leading else None,
            out_path=str(videos / "movie.yaml"),
        )

    def plan(self) -> dict[str, Any]:
        """Run only STRUCTURE (song → scenario grid) so the agent can author the script."""
        build = self._build_dir()
        build.mkdir(parents=True, exist_ok=True)
        grid = self._structure(build, StageState(str(build)))
        return {"build_dir": str(build), "scenes": grid,
                "structure_path": str(build / "structure.json"),
                "script_path": str(build / "script.json")}

    def run(self) -> dict[str, Any]:
        """Execute every stage in order (resuming finished ones); return a result dict."""
        build = self._build_dir()
        build.mkdir(parents=True, exist_ok=True)
        state = StageState(str(build))
        videos = build / "videos"
        grid = self._structure(build, state)
        script = self._script(build, grid)
        segments = self._match(build, script)
        done, failed = self._fetch(videos, segments)
        movie_yaml = self._build_playlist(build, videos, segments)
        render = self._sdk.play_playlist(movie_yaml)
        output = render.get("output_file") or render.get("saved") or movie_yaml
        stats = {"scenes": len(grid), "matched": len(segments), "downloaded": len(done),
                 "failed": len(failed), "playlist": movie_yaml, "output": output}
        report = write_report(str(build), self._cfg, stats)
        return {"build_dir": str(build), **stats, "report": report}
