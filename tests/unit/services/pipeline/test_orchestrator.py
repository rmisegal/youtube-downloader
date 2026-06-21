"""Unit tests for the fetch stage + the MoviePipeline orchestrator (SDK mocked)."""

from __future__ import annotations

import json
from pathlib import Path

from ytdl.services.pipeline.config import MovieConfig
from ytdl.services.pipeline.fetch_stage import fetch_segments
from ytdl.services.pipeline.orchestrator import MoviePipeline


def test_fetch_dedupes_same_url(tmp_path) -> None:
    segs = [
        {"sequence_number": 1, "video_url": "u-A"},
        {"sequence_number": 2, "video_url": "u-A"},  # same video → copy, not re-download
        {"sequence_number": 3, "video_url": "u-B"},
    ]
    downloaded = []

    def download(url, name, seg=None):  # noqa: ANN001 - writes <name>.mp4
        downloaded.append(url)
        (tmp_path / f"{name}.mp4").write_text("v", encoding="utf-8")

    done, failed = fetch_segments(download, segs, str(tmp_path))
    assert done == [1, 2, 3] and failed == []
    assert downloaded == ["u-A", "u-B"]  # u-A downloaded once
    assert (tmp_path / "seg_2.mp4").exists()  # scene 2 got a copy


class _FakeSDK:
    """Minimal SDK stand-in recording the pipeline's calls."""

    def __init__(self) -> None:
        self.calls = []

    def analyze_audio(self, path, **kw):  # noqa: ANN001, ANN003
        self.calls.append(("analyze", path))
        return {"metadata": {"duration_seconds": 24.0},
                "cut_points": {"bars": [{"timestamp_sec": i * 2.0} for i in range(12)]}}

    def search(self, query, *, results=6):  # noqa: ANN001
        return [{"video_url": f"u-{query}", "video_title": "T", "duration_seconds": 60}]

    def download(self, url, **kw):  # noqa: ANN001, ANN003
        self.calls.append(("download", url, kw.get("sections")))
        out = Path(kw["output_dir"]) / f"{kw['name']}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("v", encoding="utf-8")

    def build_movie(self, segments_path, video_dir, **kw):  # noqa: ANN001, ANN003
        out = kw["out_path"]
        Path(out).write_text("playlist", encoding="utf-8")
        return out

    def play_playlist(self, yaml_path):  # noqa: ANN001
        self.calls.append(("play", yaml_path))
        return {"output_file": "final.mp4"}


def _provider():
    class _P:
        def complete(self, prompt, *, system=None):  # noqa: ANN001
            return '[{"visual_description":"d","search_query":"q"}]'
    return _P()


def test_pipeline_runs_all_stages(tmp_path) -> None:
    cfg = MovieConfig(topic="space", leading="song.mp3", scene_target=3, output_dir=str(tmp_path))
    sdk = _FakeSDK()
    result = MoviePipeline(sdk, cfg, provider=_provider()).run()
    build = Path(result["build_dir"])
    assert (build / "structure.json").exists() and (build / "script.json").exists()
    assert (build / "segments.json").exists() and (build / "videos" / "movie.yaml").exists()
    assert result["scenes"] == 3 and result["matched"] == 3 and result["downloaded"] == 3
    assert result["output"] == "final.mp4"
    assert ("analyze", "song.mp3") in sdk.calls  # leading song → STRUCTURE analyzed it
    # footage is fetched as a bounded section (in-point window), not the whole video
    assert any(c[0] == "download" and c[2] is not None for c in sdk.calls)
    assert (build / "build_segments.json").exists()  # build uses in-point 0 clips


def test_pipeline_resumes_completed_structure(tmp_path) -> None:
    cfg = MovieConfig(topic="space", leading="song.mp3", scene_target=3, output_dir=str(tmp_path))
    sdk = _FakeSDK()
    MoviePipeline(sdk, cfg, provider=_provider()).run()
    sdk.calls.clear()
    MoviePipeline(sdk, cfg, provider=_provider()).run()  # second run
    assert ("analyze", "song.mp3") not in sdk.calls  # structure.json present → not re-analyzed


def test_pipeline_plan_runs_structure_only(tmp_path) -> None:
    cfg = MovieConfig(topic="space", leading="song.mp3", scene_target=3, output_dir=str(tmp_path))
    sdk = _FakeSDK()
    result = MoviePipeline(sdk, cfg).plan()
    assert len(result["scenes"]) == 3
    assert Path(result["structure_path"]).exists()
    assert not Path(result["script_path"]).exists()  # planning stops before SCRIPT
    assert not any(c[0] == "play" for c in sdk.calls)  # and before MATCH/RENDER


def test_pipeline_no_leading_skips_analyze(tmp_path) -> None:
    cfg = MovieConfig(topic="x", leading="", scene_target=4, output_dir=str(tmp_path))
    sdk = _FakeSDK()
    result = MoviePipeline(sdk, cfg, provider=_provider()).run()
    assert result["scenes"] == 4
    assert not any(c[0] == "analyze" for c in sdk.calls)  # no song → no analysis
    grid = json.loads((Path(result["build_dir"]) / "structure.json").read_text(encoding="utf-8"))
    assert len(grid) == 4
