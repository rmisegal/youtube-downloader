"""Unit tests for the content-target lookup table + pacing rules."""

from __future__ import annotations

from ytdl.services.analysis.profiles import (
    CONTENT_TARGETS,
    HOLD_HALF_BAR,
    HOLD_UNIQUE,
    get_profile,
    hold_for,
    mood_from_bpm,
)

EXPECTED_TARGETS = {
    "video_art", "dj_party", "homemade", "presentation", "podcast",
    "road_travel", "topic_summary", "lecture",
}


def test_all_eight_content_targets_exist() -> None:
    assert set(CONTENT_TARGETS) >= EXPECTED_TARGETS
    for prof in CONTENT_TARGETS.values():
        assert prof.transitions and prof.rhythm and prof.hold_beats >= HOLD_HALF_BAR


def test_get_profile_falls_back_to_default() -> None:
    assert get_profile("nonsense").transitions == CONTENT_TARGETS["video_art"].transitions
    assert get_profile(None).hold_beats == CONTENT_TARGETS["video_art"].hold_beats


def test_mood_from_bpm_bands() -> None:
    assert mood_from_bpm(80) == "calm"
    assert mood_from_bpm(110) == "groovy"
    assert mood_from_bpm(140) == "energetic"


def test_unique_mode_only_at_build_up_and_only_if_enabled() -> None:
    art = get_profile("video_art")          # unique enabled
    assert hold_for(art, "Build-up", "groovy") == (HOLD_UNIQUE, True)
    assert hold_for(art, "Verse", "groovy")[1] is False  # not unique elsewhere
    home = get_profile("homemade")          # unique disabled
    assert home.unique_hold_beats is None
    assert hold_for(home, "Build-up", "groovy")[1] is False  # never beat-by-beat


def test_standard_hold_never_below_half_bar() -> None:
    art = get_profile("video_art")
    for section in ("Verse", "Chorus", "Intro", "Outro"):
        hold, unique = hold_for(art, section, "energetic")
        assert hold >= HOLD_HALF_BAR and not unique


def test_calm_sections_hold_longer_than_chorus() -> None:
    art = get_profile("video_art")
    intro = hold_for(art, "Intro", "groovy")[0]
    chorus = hold_for(art, "Chorus", "groovy")[0]
    assert intro > chorus  # Intro lingers; Chorus tightens to a half-bar
