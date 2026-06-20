"""Tiers 2-3 — derive bars (downbeats) and phrases from librosa beats.

librosa has no native downbeat detector (madmom does, but is incompatible with
our Python 3.12; it is the optional sidecar). Here bars group beats by ``meter``
(default 4/4) with the downbeat = the beat in each group whose onset strength is
strongest (a cheap downbeat heuristic); phrases group bars by ``phrase_bars``.
Pure logic — no DSP — so it is fully unit-testable.
"""

from __future__ import annotations

from collections.abc import Sequence


def _strength_at(time_sec: float, onsets: Sequence[float], window: float = 0.07) -> int:
    """1 when an onset lands within ``window`` of ``time_sec`` (cheap accent score)."""
    return 1 if any(abs(o - time_sec) <= window for o in onsets) else 0


def build_bars(
    beats: Sequence[float], onsets: Sequence[float], *, meter: int = 4
) -> list[dict[str, float | int]]:
    """Group beats into bars; the downbeat is the strongest-onset beat per group."""
    bars: list[dict[str, float | int]] = []
    for bar_idx, start in enumerate(range(0, len(beats), max(1, meter)), start=1):
        group = list(range(start, min(start + meter, len(beats))))
        if not group:
            break
        downbeat = max(group, key=lambda i: _strength_at(beats[i], onsets))
        # Keep the bar anchored at the group's first beat, but record the accent.
        bars.append({"timestamp_sec": float(beats[start]), "bar_index": bar_idx,
                     "accent_sec": float(beats[downbeat])})
    return bars


def build_phrases(
    bars: Sequence[dict[str, float | int]], *, phrase_bars: int = 8
) -> list[dict[str, float | str]]:
    """Group bars into 4/8-bar phrases; label A_Start then B/C/... _Transition."""
    phrases: list[dict[str, float | str]] = []
    for n, start in enumerate(range(0, len(bars), max(1, phrase_bars))):
        label = "Phrase_A_Start" if n == 0 else f"Phrase_{chr(65 + (n % 25))}_Transition"
        phrases.append({"timestamp_sec": float(bars[start]["timestamp_sec"]), "phrase_type": label})
    return phrases
