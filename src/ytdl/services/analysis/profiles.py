"""Hardcoded content-target lookup table for music-synced pacing (PRD-beatsync).

Removes any need for runtime LLM analysis of the leading track: each CONTENT TARGET
(Video Art, DJ Party, Homemade, Presentation, Podcast, Road-Travel Audio Mix, Topic
Summary, Lecture) maps to a fixed :class:`ContentProfile` of three core parameters —

  1. ``transitions``  : the pool of available visual transitions (pulled at random),
  2. ``rhythm``       : the rhythmic transition type (how cuts sync to the mood/tempo),
  3. ``hold_beats``   : the display duration in BEATS an object stays before replacement.

Standard playback holds for a full bar (4 beats) or a half-measure (2 beats); the
beat-by-beat hold (1) is a "Unique Mode" reserved for high-impact transitional
sections (build-ups / drops). The execution code pulls a transition at RANDOM and the
hold CONDITIONALLY from the track's mood — creative, surprising mixes with no LLM.
"""

from __future__ import annotations

from dataclasses import dataclass

from ytdl.constants import (
    SECTION_BUILD,
    SECTION_CHORUS,
    SECTION_INTRO,
    SECTION_OUTRO,
    TRANSITION_BOUNCE,
    TRANSITION_FADE,
    TRANSITION_FLASH,
    TRANSITION_PANDOWN,
    TRANSITION_PANLEFT,
    TRANSITION_PANRIGHT,
    TRANSITION_PANUP,
    TRANSITION_PULSE,
    TRANSITION_SHAKE,
    TRANSITION_ZOOMIN,
    TRANSITION_ZOOMOUT,
)

# Display-duration grid (beats), 4/4 time. Standard = full bar / half-measure.
HOLD_FULL_BAR = 4
HOLD_HALF_BAR = 2
HOLD_UNIQUE = 1  # beat-by-beat — Unique Mode only
# Unique Mode is "highly specific": the beat-by-beat burst is limited to the last
# few beats of a high-impact section (the rapid run-up to the drop); the earlier part
# of that section still holds a half-bar.
UNIQUE_TAIL_BEATS = 8

# Track mood (from BPM) — conditionally tightens the hold.
MOOD_CALM = "calm"
MOOD_GROOVY = "groovy"
MOOD_ENERGETIC = "energetic"

# Where beat-by-beat Unique Mode may trigger, which sections speed up / slow down.
HIGH_IMPACT_SECTIONS = (SECTION_BUILD,)
ENERGETIC_SECTIONS = (SECTION_CHORUS,)
CALM_SECTIONS = (SECTION_INTRO, SECTION_OUTRO)


@dataclass(frozen=True)
class ContentProfile:
    """The three core sync parameters for one content target."""

    transitions: tuple[str, ...]          # 1. available visual transitions (random pool)
    rhythm: str                           # 2. rhythmic transition type
    hold_beats: int                       # 3. standard display duration in beats (4 or 2)
    unique_hold_beats: int | None = None  # Unique-Mode hold (1) at high-impact; None disables


_ALL = (
    TRANSITION_FADE, TRANSITION_ZOOMIN, TRANSITION_ZOOMOUT, TRANSITION_PANLEFT,
    TRANSITION_PANRIGHT, TRANSITION_PANUP, TRANSITION_PANDOWN, TRANSITION_PULSE,
    TRANSITION_SHAKE, TRANSITION_BOUNCE, TRANSITION_FLASH,
)

# The hardcoded matrix: content target -> (transitions, rhythm, hold, unique-hold).
CONTENT_TARGETS: dict[str, ContentProfile] = {
    "video_art": ContentProfile(_ALL, "atmospheric", HOLD_FULL_BAR, HOLD_UNIQUE),
    "dj_party": ContentProfile(
        (TRANSITION_PULSE, TRANSITION_FLASH, TRANSITION_SHAKE, TRANSITION_BOUNCE,
         TRANSITION_ZOOMIN), "energetic", HOLD_HALF_BAR, HOLD_UNIQUE),
    "homemade": ContentProfile(
        (TRANSITION_FADE, TRANSITION_ZOOMIN, TRANSITION_ZOOMOUT, TRANSITION_PANLEFT,
         TRANSITION_PANRIGHT), "gentle", HOLD_FULL_BAR, None),
    "presentation": ContentProfile(
        (TRANSITION_FADE, TRANSITION_ZOOMIN), "steady", HOLD_FULL_BAR * 2, None),
    "podcast": ContentProfile(
        (TRANSITION_FADE, TRANSITION_ZOOMOUT), "minimal", HOLD_FULL_BAR * 4, None),
    "road_travel": ContentProfile(
        (TRANSITION_PANLEFT, TRANSITION_PANRIGHT, TRANSITION_ZOOMOUT, TRANSITION_FADE),
        "flowing", HOLD_FULL_BAR, None),
    "topic_summary": ContentProfile(
        (TRANSITION_FADE, TRANSITION_ZOOMIN, TRANSITION_PANRIGHT), "steady",
        HOLD_FULL_BAR, None),
    "lecture": ContentProfile(
        (TRANSITION_FADE, TRANSITION_ZOOMIN), "steady", HOLD_FULL_BAR * 2, None),
}
DEFAULT_TARGET = "video_art"


def get_profile(target: str | None) -> ContentProfile:
    """Return the profile for a content target (falls back to the default)."""
    key = (target or DEFAULT_TARGET).strip().lower()
    return CONTENT_TARGETS.get(key, CONTENT_TARGETS[DEFAULT_TARGET])


def mood_from_bpm(bpm: float) -> str:
    """Classify the track's mood from its tempo (the conditional pacing input)."""
    if bpm < 95:
        return MOOD_CALM
    if bpm > 128:
        return MOOD_ENERGETIC
    return MOOD_GROOVY


def hold_for(profile: ContentProfile, section: str, mood: str) -> tuple[int, bool]:
    """Return ``(hold_beats, is_unique)`` for a section under the track's mood.

    Unique Mode (beat-by-beat) only at high-impact sections AND only if the profile
    enables it; otherwise STANDARD playback holds for a full bar (4) or half-bar (2) —
    slowed in calm sections (Intro/Outro), tightened to a half-bar in the Chorus or an
    energetic-tempo track. The standard hold is never shorter than a half-bar.
    """
    if section in HIGH_IMPACT_SECTIONS and profile.unique_hold_beats:
        return profile.unique_hold_beats, True
    base = profile.hold_beats
    if section in CALM_SECTIONS:
        base *= 2
    elif section in ENERGETIC_SECTIONS or mood == MOOD_ENERGETIC:
        base = max(HOLD_HALF_BAR, base // 2)
    return max(HOLD_HALF_BAR, base), False
