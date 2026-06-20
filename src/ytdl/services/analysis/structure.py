"""Tier 4 — structural sections (Intro/Verse/Build-up/Chorus/Outro).

Boundaries come from librosa's agglomerative clustering of chroma features; the
semantic labels are a HEURISTIC over onset density + position (documented as
approximate — true labels would need an ML model). ``label_sections`` is pure
logic (segments + onsets → labels) so it is fully unit-testable without DSP.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ytdl.constants import (
    SECTION_BUILD,
    SECTION_CHORUS,
    SECTION_INTRO,
    SECTION_OUTRO,
    SECTION_VERSE,
)

Section = dict[str, Any]


def section_boundaries(
    samples: Any, sr: int, duration: float, beat_frames: Sequence[int],
    beat_times: Sequence[float], *, librosa_mod: Any = None,
) -> list[float]:
    """Return sorted boundary times (incl. 0 and ``duration``) via librosa.

    Clusters BEAT-SYNCHRONOUS chroma (≈one column per beat) rather than the ~8000
    raw frames — agglomerative on the synced matrix is ~instant vs ~2s on raw
    frames, which keeps the whole analysis under the <10s NFR.
    """
    if librosa_mod is None:
        import librosa as librosa_mod  # noqa: PLC0415 - lazy heavy import
    k = max(2, min(8, round(duration / 30.0)))
    # chroma_stft (FFT) is far faster than chroma_cqt and ample for clustering.
    chroma = librosa_mod.feature.chroma_stft(y=samples, sr=sr)
    if len(beat_frames) >= max(4, k):
        synced = librosa_mod.util.sync(chroma, beat_frames)
        idx = librosa_mod.segment.agglomerative(synced, k)
        bt = list(beat_times)
        times = [float(bt[min(int(i), len(bt) - 1)]) for i in idx]
    else:
        idx = librosa_mod.segment.agglomerative(chroma, k)
        times = [float(t) for t in librosa_mod.frames_to_time(idx, sr=sr)]
    return sorted({0.0, *times, float(duration)})


def _density(start: float, end: float, onsets: Sequence[float]) -> float:
    """Onsets per second within ``[start, end)`` (a cheap energy proxy)."""
    span = max(1e-6, end - start)
    return sum(1 for o in onsets if start <= o < end) / span


def label_sections(boundaries: Sequence[float], onsets: Sequence[float]) -> list[Section]:
    """Label consecutive segments by position + onset density (heuristic)."""
    segs = [(boundaries[i], boundaries[i + 1]) for i in range(len(boundaries) - 1)]
    if not segs:
        return []
    dens = [_density(s, e, onsets) for s, e in segs]
    peak = max(dens) if dens else 0.0
    out: list[Section] = []
    n = len(segs)
    for i, (start, end) in enumerate(segs):
        if i == 0:
            label = SECTION_INTRO
        elif i == n - 1:
            label = SECTION_OUTRO
        elif peak and dens[i] >= 0.8 * peak:
            label = SECTION_CHORUS
        elif i + 1 < n and peak and dens[i + 1] >= 0.8 * peak and dens[i] < dens[i + 1]:
            label = SECTION_BUILD
        else:
            label = SECTION_VERSE
        out.append({"start_sec": round(start, 3), "end_sec": round(end, 3), "label": label})
    return out


def extract_sections(
    samples: Any, sr: int, duration: float, beat_frames: Sequence[int],
    beat_times: Sequence[float], onsets: Sequence[float], *, librosa_mod: Any = None,
) -> list[Section]:
    """Beat-synchronous boundaries (librosa) + heuristic labels."""
    bounds = section_boundaries(
        samples, sr, duration, beat_frames, beat_times, librosa_mod=librosa_mod
    )
    return label_sections(bounds, onsets)
