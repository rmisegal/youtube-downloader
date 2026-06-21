"""Unit tests for the hold-based Context-Aware Cut Planner (pure logic)."""

from __future__ import annotations

import random

from ytdl.services.analysis.cut_planner import plan_cuts
from ytdl.services.analysis.profiles import ContentProfile, get_profile

# 16 quarter-note beats at 1s apart, a Verse then a Build-up.
CP = {
    "beats": [{"timestamp_sec": float(t)} for t in range(16)],
    "sections": [
        {"start_sec": 0.0, "end_sec": 8.0, "label": "Verse"},
        {"start_sec": 8.0, "end_sec": 16.0, "label": "Build-up"},
    ],
}
PROF = ContentProfile(("fade", "pulse"), "test", hold_beats=4, unique_hold_beats=1)


def test_standard_holds_full_bar_not_every_beat() -> None:
    cuts = plan_cuts(CP, PROF, mood="groovy", rng=random.Random(0))
    verse = [c for c in cuts if c["section"] == "Verse"]
    # Verse holds 4 beats -> cuts at 0,4 (NOT every beat). hold_beats recorded as 4.
    assert [c["timestamp_sec"] for c in verse] == [0.0, 4.0]
    assert all(c["hold_beats"] == 4 and not c["unique"] for c in verse)


def test_unique_mode_is_beat_by_beat_only_at_high_impact() -> None:
    cuts = plan_cuts(CP, PROF, mood="groovy", rng=random.Random(0))
    build = [c for c in cuts if c["section"] == "Build-up"]
    # Build-up = Unique Mode -> every beat (8..15), hold 1, flagged unique.
    assert [c["timestamp_sec"] for c in build] == [float(t) for t in range(8, 16)]
    assert all(c["hold_beats"] == 1 and c["unique"] for c in build)


def test_transition_is_pulled_from_profile_pool() -> None:
    cuts = plan_cuts(CP, PROF, rng=random.Random(1))
    # Non-boundary cuts come from the profile pool; the only exception is the
    # dramatic fade-to-black at a section change.
    assert all(c["transition"] in PROF.transitions or c["transition"] == "fadeblack" for c in cuts)


def test_black_only_at_section_boundaries() -> None:
    cuts = plan_cuts(CP, PROF, mood="groovy", rng=random.Random(0))
    blacks = [c for c in cuts if c["transition"] == "fadeblack"]
    # CP has two sections -> exactly one boundary (start of the 2nd section); the
    # very first cut is never black.
    assert len(blacks) == 1
    assert blacks[0]["section"] == "Build-up"
    assert cuts[0]["transition"] != "fadeblack"


def test_no_black_mode_suppresses_fadeblack() -> None:
    cuts = plan_cuts(CP, PROF, mood="groovy", no_black=True, rng=random.Random(0))
    assert all(c["transition"] != "fadeblack" for c in cuts)  # crossfade mode = never dark


def test_fixed_mode_overrides_to_constant_grid() -> None:
    half = plan_cuts(CP, PROF, mode="half", rng=random.Random(0))
    # mode=half -> hold 2 beats everywhere (0,2,4,...).
    assert [c["timestamp_sec"] for c in half][:3] == [0.0, 2.0, 4.0]
    assert all(c["hold_beats"] == 2 for c in half)


def test_profile_without_unique_never_goes_beat_by_beat() -> None:
    gentle = ContentProfile(("fade",), "gentle", hold_beats=4, unique_hold_beats=None)
    cuts = plan_cuts(CP, gentle, mood="groovy", rng=random.Random(0))
    assert all(c["hold_beats"] >= 2 and not c["unique"] for c in cuts)  # never 1


def test_first_cut_anchored_at_zero() -> None:
    cp = {"beats": [{"timestamp_sec": 1.5}, {"timestamp_sec": 2.0}],
          "sections": [{"start_sec": 0.0, "end_sec": 3.0, "label": "Verse"}]}
    cuts = plan_cuts(cp, get_profile("video_art"), rng=random.Random(0))
    assert cuts[0]["timestamp_sec"] == 0.0  # concat-safe coverage from the start


def test_empty_beats_returns_empty() -> None:
    assert plan_cuts({}, PROF) == []
