"""Unit tests for the Context-Aware Cut Planner (pure logic)."""

from __future__ import annotations

from ytdl.services.analysis.cut_planner import plan_cuts

CP = {
    "beats": [{"timestamp_sec": float(t)} for t in range(8)],
    "bars": [{"timestamp_sec": 0.0}, {"timestamp_sec": 4.0}],
    "phrases": [{"timestamp_sec": 0.0}],
    "sections": [
        {"start_sec": 0.0, "end_sec": 4.0, "label": "Verse"},
        {"start_sec": 4.0, "end_sec": 8.0, "label": "Chorus"},
    ],
}


def test_auto_is_section_driven() -> None:
    plan = plan_cuts(CP, mode="auto", section_rules={"Verse": "bar", "Chorus": "beat"},
                     fill_on_phrase_end=False)
    by_time = {c["timestamp_sec"]: c for c in plan}
    assert by_time[0.0]["tier"] == "bar"  # Verse -> bar
    assert by_time[4.0]["tier"] == "beat" and by_time[5.0]["tier"] == "beat"  # Chorus -> beat
    assert by_time[4.0]["section"] == "Chorus"  # carries the section for transition fitting


def test_fixed_mode_uses_one_tier() -> None:
    plan = plan_cuts(CP, mode="beat")
    assert len(plan) == 8
    assert all(c["tier"] == "beat" for c in plan)


def test_phrase_end_fills_add_quick_beats() -> None:
    cp = {**CP, "phrases": [{"timestamp_sec": 4.0}]}
    plan = plan_cuts(cp, mode="auto", section_rules={"Verse": "bar", "Chorus": "beat"},
                     fill_on_phrase_end=True, n_fill=2)
    fills = {c["timestamp_sec"] for c in plan if c["section"] == "fill"}
    assert {2.0, 3.0} <= fills  # the 2 beats before the phrase boundary


def test_empty_returns_empty() -> None:
    assert plan_cuts({}, mode="auto") == []
