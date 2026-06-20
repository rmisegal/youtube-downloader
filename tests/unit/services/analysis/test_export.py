"""Unit tests for result assembly + JSON/CSV export (frame-index math)."""

from __future__ import annotations

import json
from pathlib import Path

from ytdl.services.analysis.export import build_result, write_csv, write_json


def _res():
    return build_result(
        file_name="s.mp3", duration=10.0, bpm=120.0, fps=30.0, device="cpu",
        beats=[0.5, 1.0], bars=[{"timestamp_sec": 0.5, "bar_index": 1}],
        phrases=[{"timestamp_sec": 0.5, "phrase_type": "Phrase_A_Start"}],
        sections=[{"start_sec": 0.0, "end_sec": 10.0, "label": "Intro"}],
        levels=["beat", "bar", "phrase", "section"],
    )


def test_frame_index_is_seconds_times_fps() -> None:
    r = _res()
    assert r["cut_points"]["beats"][0]["frame_index"] == 15  # 0.5 * 30
    assert r["cut_points"]["beats"][1]["frame_index"] == 30
    assert r["cut_points"]["bars"][0]["frame_index"] == 15
    assert r["metadata"]["global_bpm"] == 120.0
    assert r["metadata"]["device"] == "cpu"
    assert r["metadata"]["target_fps"] == 30.0


def test_levels_filter_emits_only_requested() -> None:
    r = build_result(
        file_name="s", duration=1, bpm=100, fps=30, device="cpu",
        beats=[0.1], bars=[], phrases=[], sections=[], levels=["beat"],
    )
    assert set(r["cut_points"]) == {"beats"}


def test_write_json_and_csv(tmp_path) -> None:
    r = _res()
    j = write_json(r, str(tmp_path / "o.json"))
    data = json.loads(Path(j).read_text(encoding="utf-8"))
    assert data["metadata"]["file_name"] == "s.mp3"
    assert data["cut_points"]["sections"][0]["label"] == "Intro"
    c = write_csv(r, str(tmp_path / "o.csv"))
    text = Path(c).read_text(encoding="utf-8")
    assert "tier" in text and "beats" in text and "Intro" in text
