"""Context-Aware Cut Planner (PRD-beatsync §4).

The SECTION level dictates the cut tier per segment (config ``section_rules``):
Intro/Outro→phrase (slow), Verse→bar (steady), Build-up/Chorus→beat (energetic).
Phrase ends optionally get a drum-fill of quick beat cuts ("visual punctuation").

Each emitted cut carries its ``tier`` + ``section`` so the caller can FIT THE
TRANSITION to the musical sync type (fast on a beat, slow on a phrase, …). Pure
logic — no DSP — fully unit-testable.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ytdl.constants import (
    SECTION_CHORUS,
    SECTION_INTRO,
    SECTION_OUTRO,
    SECTION_VERSE,
    TIER_BAR,
    TIER_BEAT,
    TIER_PHRASE,
    TIER_SECTION,
)

DEFAULT_RULES: dict[str, str] = {
    SECTION_INTRO: TIER_PHRASE, SECTION_VERSE: TIER_BAR, "Build-up": TIER_BEAT,
    SECTION_CHORUS: TIER_BEAT, SECTION_OUTRO: TIER_PHRASE,
}
Cut = dict[str, Any]


def _tier_times(tier: str, lists: dict[str, list[float]]) -> list[float]:
    return lists.get(tier, lists[TIER_BAR])


def _lists(cut_points: Mapping[str, Any]) -> dict[str, list[float]]:
    sections = cut_points.get("sections", [])
    return {
        TIER_BEAT: [b["timestamp_sec"] for b in cut_points.get("beats", [])],
        TIER_BAR: [b["timestamp_sec"] for b in cut_points.get("bars", [])],
        TIER_PHRASE: [p["timestamp_sec"] for p in cut_points.get("phrases", [])],
        TIER_SECTION: [s["start_sec"] for s in sections],
    }


def _fills(phrases: Sequence[float], beats: Sequence[float], n_fill: int) -> dict[float, tuple[str, str]]:
    out: dict[float, tuple[str, str]] = {}
    for p in phrases:
        for b in [x for x in beats if x < p][-n_fill:]:
            out[b] = (TIER_BEAT, "fill")
    return out


def plan_cuts(
    cut_points: Mapping[str, Any], *, mode: str = "auto",
    section_rules: Mapping[str, str] | None = None,
    fill_on_phrase_end: bool = True, n_fill: int = 3,
) -> list[Cut]:
    """Return ordered cut entries ``{timestamp_sec, tier, section}``.

    ``mode != "auto"`` uses that single tier everywhere; ``"auto"`` is the
    section-driven strategy + phrase-end fills.
    """
    lists = _lists(cut_points)
    plan: dict[float, tuple[str, str]] = {}
    if mode != "auto":
        for t in _tier_times(mode, lists):
            plan.setdefault(t, (mode, ""))
    else:
        rules = {**DEFAULT_RULES, **(section_rules or {})}
        for sec in cut_points.get("sections", []):
            tier = rules.get(sec["label"], TIER_BAR)
            within = [t for t in _tier_times(tier, lists)
                      if sec["start_sec"] <= t < sec["end_sec"]]
            for t in [sec["start_sec"], *within]:
                plan[t] = (tier, sec["label"])
        if fill_on_phrase_end:
            for t, value in _fills(lists[TIER_PHRASE], lists[TIER_BEAT], n_fill).items():
                plan.setdefault(t, value)
    return [{"timestamp_sec": round(t, 3), "tier": tr, "section": lab}
            for t, (tr, lab) in sorted(plan.items()) if t >= 0]
