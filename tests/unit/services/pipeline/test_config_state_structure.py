"""Unit tests for the pipeline config, stage-state, and scenario grid."""

from __future__ import annotations

from ytdl.services.pipeline.config import CONFIG_VERSION, MovieConfig
from ytdl.services.pipeline.state import StageState
from ytdl.services.pipeline.structure import build_scenario_grid


def _analysis(bars, total, sections=None):
    return {
        "metadata": {"duration_seconds": total},
        "cut_points": {"bars": [{"timestamp_sec": b} for b in bars], "sections": sections or []},
    }


def test_config_roundtrip_and_version(tmp_path) -> None:
    cfg = MovieConfig(idea="space", leading="song.mp3", scene_target=8)
    path = cfg.save(str(tmp_path / "config.json"))
    loaded = MovieConfig.load(path)
    assert loaded.idea == "space" and loaded.scene_target == 8
    assert loaded.version == CONFIG_VERSION


def test_config_load_ignores_unknown_keys(tmp_path) -> None:
    p = tmp_path / "c.json"
    p.write_text('{"idea":"x","FUTURE_KEY":1}', encoding="utf-8")
    assert MovieConfig.load(str(p)).idea == "x"


def test_stages_depend_on_leading() -> None:
    assert "structure" in MovieConfig(leading="s.mp3").stages
    assert "structure" not in MovieConfig(leading="").stages  # no song → no beat structure


def test_stage_state_resume(tmp_path) -> None:
    st = StageState(str(tmp_path))
    assert not st.is_done("script")
    (tmp_path / "script.json").write_text("[]", encoding="utf-8")
    st.mark_done("script")
    assert StageState(str(tmp_path)).is_done("script")  # persisted + artifact present
    (tmp_path / "script.json").unlink()
    assert not StageState(str(tmp_path)).is_done("script")  # artifact gone → re-run


def test_scenario_grid_target_and_sections() -> None:
    bars = [i * 2.0 for i in range(40)]  # 40 bars, 0..78s
    sections = [{"start_sec": 0, "label": "intro"}, {"start_sec": 20, "label": "chorus"}]
    grid = build_scenario_grid(_analysis(bars, 80.0, sections), target=8)
    assert len(grid) == 8
    assert grid[0]["index"] == 1 and grid[0]["section"] == "intro"
    assert grid[-1]["section"] == "chorus"
    assert grid[0]["until"] > grid[0]["at"]  # each slot has positive length


def test_scenario_grid_fewer_bars_than_target() -> None:
    grid = build_scenario_grid(_analysis([0.0, 4.0, 8.0], 12.0), target=10)
    assert 1 <= len(grid) <= 3  # never more slots than bars, never zero


def test_scenario_grid_no_bars_even_split() -> None:
    grid = build_scenario_grid(_analysis([], 60.0), target=6)
    assert len(grid) == 6 and grid[0]["at"] == 0.0
