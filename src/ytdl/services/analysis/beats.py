"""Tier 1 — librosa beats, onsets, and tempo (micro-rhythm).

Returns plain Python floats/lists (not numpy) so downstream planner/export code
and tests stay numpy-agnostic. ``librosa`` is injectable for tests.
"""

from __future__ import annotations

from typing import Any


def _to_float(value: Any) -> float:
    """Coerce a scalar or 1-element array to ``float``."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(value[0])


def extract_beats(samples: Any, sr: int, *, librosa_mod: Any = None) -> dict[str, Any]:
    """Extract tempo (BPM), beat times/frames, and onset times (seconds).

    Computes the onset-strength envelope ONCE and feeds it to both ``beat_track``
    and ``onset_detect`` (avoids recomputing it twice). ``beat_frames`` is returned
    for beat-synchronous structure analysis.
    """
    if librosa_mod is None:
        import librosa as librosa_mod  # noqa: PLC0415 - lazy heavy import
    onset_env = librosa_mod.onset.onset_strength(y=samples, sr=sr)
    tempo, beat_frames = librosa_mod.beat.beat_track(onset_envelope=onset_env, sr=sr)
    onset_frames = librosa_mod.onset.onset_detect(onset_envelope=onset_env, sr=sr)
    return {
        "bpm": _to_float(tempo),
        "beats": [float(t) for t in librosa_mod.frames_to_time(beat_frames, sr=sr)],
        "beat_frames": [int(f) for f in beat_frames],
        "onsets": [float(t) for t in librosa_mod.frames_to_time(onset_frames, sr=sr)],
        "sr": int(sr),
    }
