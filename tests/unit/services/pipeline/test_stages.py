"""Unit tests for the SCRIPT / MATCH / REPORT pipeline stages."""

from __future__ import annotations

from ytdl.services.pipeline.config import MovieConfig
from ytdl.services.pipeline.match_stage import _pick, _start_hms, match_scenes
from ytdl.services.pipeline.report import write_report
from ytdl.services.pipeline.script_stage import align_to_grid, build_prompt, generate_script

GRID = [
    {"index": 1, "at": 0.0, "duration": 6.0, "section": "intro"},
    {"index": 2, "at": 6.0, "duration": 6.0, "section": "chorus"},
]


def test_build_prompt_mentions_topic_and_scene_count() -> None:
    prompt = build_prompt(MovieConfig(topic="space travel"), GRID)
    assert "space travel" in prompt and "Plan 2 sequential scenes" in prompt


def test_align_to_grid_fills_missing_and_aligns() -> None:
    raw = [{"visual_description": "rocket", "search_query": "rocket launch"}]  # only 1 of 2
    script = align_to_grid(raw, GRID)
    assert len(script) == 2
    assert script[0]["search_query"] == "rocket launch"
    assert script[1]["search_query"] == "chorus"  # gap → falls back to the section label
    assert [s["scenario_number"] for s in script] == [1, 2]


def test_generate_script_with_fake_provider() -> None:
    class _P:
        def complete(self, prompt, *, system=None):  # noqa: ANN001
            return 'noise [{"visual_description":"a","search_query":"qa"},' \
                   '{"visual_description":"b","search_query":"qb"}] trailing'
    script = generate_script(_P(), MovieConfig(), GRID)
    assert script[0]["search_query"] == "qa" and script[1]["search_query"] == "qb"


def test_pick_prefers_long_enough_else_longest() -> None:
    cands = [{"video_url": "a", "duration_seconds": 4}, {"video_url": "b", "duration_seconds": 30}]
    assert _pick(cands, need_sec=10)["video_url"] == "b"
    assert _pick([{"video_url": "a", "duration_seconds": 4}], need_sec=10)["video_url"] == "a"
    assert _pick([], need_sec=5) is None


def test_start_hms_leaves_room() -> None:
    assert _start_hms(0, 6) == "00:00:00"
    assert _start_hms(100, 6) != "00:00:00"  # long source → a mid in-point


def test_match_scenes_searches_and_resumes(tmp_path) -> None:
    script = align_to_grid([], GRID)
    calls = []

    def search_fn(query, results):  # noqa: ANN001
        calls.append(query)
        return [{"video_url": f"u-{query}", "video_title": "T", "duration_seconds": 60}]

    segs = match_scenes(search_fn, script, str(tmp_path))
    assert len(segs) == 2 and segs[0]["sequence_number"] == 1
    assert (tmp_path / "scenarios" / "scn_1.json").exists()
    # second run resumes from cache → no new searches
    calls.clear()
    again = match_scenes(search_fn, script, str(tmp_path))
    assert calls == [] and again == segs


def test_write_report(tmp_path) -> None:
    from pathlib import Path
    out = write_report(str(tmp_path), MovieConfig(topic="x", leading="s.mp3"),
                        {"scenes": 2, "matched": 2, "downloaded": 1, "output": "final.mp4"})
    txt = Path(out).read_text(encoding="utf-8")
    assert "scenes planned: 2" in txt and "final.mp4" in txt and "beat-sync" in txt
