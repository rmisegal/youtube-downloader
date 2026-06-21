"""Context-aware Cut Planner (PRD-beatsync §4).

Walks the BEAT grid and **holds each object for a number of beats** taken from the
content-target profile (see :mod:`profiles`): a full bar (4) or a half-bar (2) for
standard playback, dropping to **beat-by-beat (1) only in the "Unique Mode"** of
high-impact sections (build-ups / drops). This fixes the "switches on every beat"
problem — standard playback now lingers. Each emitted cut carries a transition
pulled at RANDOM from the profile's pool (the dynamic selection matrix). Pure logic.
"""

from __future__ import annotations

import random as _random
from collections.abc import Mapping, Sequence
from typing import Any

from ytdl.services.analysis.profiles import (
    HOLD_HALF_BAR,
    HOLD_UNIQUE,
    UNIQUE_TAIL_BEATS,
    ContentProfile,
    hold_for,
)

Cut = dict[str, Any]
# Fixed-grid overrides via metadata.sync.mode: a constant hold in beats.
FIXED_HOLDS = {"beat": 1, "half": 2, "bar": 4, "phrase": 8}


def _in_section(beats: Sequence[float], start: float, end: float) -> list[float]:
    return [t for t in beats if start <= t < end]


def _picks(sec_beats: list[float], hold: int, unique: bool) -> list[tuple[float, int, bool]]:
    """Beats to cut on within a section as ``(time, hold_beats, is_unique)``.

    Standard: every ``hold`` beats. Unique Mode: a half-bar lead-in, then beat-by-beat
    only across the final :data:`UNIQUE_TAIL_BEATS` (the run-up to the drop).
    """
    if not unique:
        return [(t, hold, False) for t in sec_beats[:: max(1, hold)]]
    if len(sec_beats) <= UNIQUE_TAIL_BEATS:
        return [(t, HOLD_UNIQUE, True) for t in sec_beats]
    lead, tail = sec_beats[:-UNIQUE_TAIL_BEATS], sec_beats[-UNIQUE_TAIL_BEATS:]
    return ([(t, HOLD_HALF_BAR, False) for t in lead[::HOLD_HALF_BAR]]
            + [(t, HOLD_UNIQUE, True) for t in tail])


def plan_cuts(
    cut_points: Mapping[str, Any], profile: ContentProfile, *,
    mood: str = "groovy", mode: str = "auto", rng: Any = _random,
) -> list[Cut]:
    """Return ordered cuts ``{timestamp_sec, transition, section, hold_beats, unique}``.

    ``mode="auto"`` is the profile/mood-driven pacing; a fixed name in
    :data:`FIXED_HOLDS` (or ``"section"``) forces a constant grid.
    """
    beats = [b["timestamp_sec"] for b in cut_points.get("beats", [])]
    if not beats:
        return []
    sections = cut_points.get("sections", []) or [
        {"start_sec": 0.0, "end_sec": beats[-1] + 1.0, "label": ""}
    ]
    cuts: list[Cut] = []
    for sec in sections:
        sec_beats = _in_section(beats, sec["start_sec"], sec["end_sec"])
        if not sec_beats:
            continue
        if mode == "section":
            picks = [(sec_beats[0], len(sec_beats), False)]
        elif mode in FIXED_HOLDS:
            picks = _picks(sec_beats, FIXED_HOLDS[mode], mode == "beat")
        else:
            hold, unique = hold_for(profile, sec.get("label", ""), mood)
            picks = _picks(sec_beats, hold, unique)
        for t, hold_beats, unique in picks:
            cuts.append({
                "timestamp_sec": round(float(t), 3),
                "transition": rng.choice(profile.transitions),
                "section": sec.get("label", ""), "hold_beats": hold_beats, "unique": unique,
            })
    cuts.sort(key=lambda c: c["timestamp_sec"])
    # Anchor the first cut at the song start so the slots cover [0, total) (concat-safe).
    if cuts and cuts[0]["timestamp_sec"] > 0:
        cuts[0] = {**cuts[0], "timestamp_sec": 0.0}
    return cuts
