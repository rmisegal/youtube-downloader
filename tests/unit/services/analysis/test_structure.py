"""Unit tests for section labeling (pure) + boundary extraction (mocked librosa)."""

from __future__ import annotations

from unittest.mock import MagicMock

from ytdl.services.analysis.structure import (
    label_sections,
    section_boundaries,
)


def test_label_sections_intro_outro_and_chorus() -> None:
    boundaries = [0.0, 10.0, 20.0, 30.0, 40.0]  # 4 segments
    onsets = list(range(20, 30))  # dense onsets in segment index 2 -> Chorus
    secs = label_sections(boundaries, onsets)
    labels = [s["label"] for s in secs]
    assert labels[0] == "Intro"
    assert labels[-1] == "Outro"
    assert "Chorus" in labels
    assert secs[0]["start_sec"] == 0.0 and secs[-1]["end_sec"] == 40.0


def test_label_sections_no_segments() -> None:
    assert label_sections([0.0], []) == []


def test_section_boundaries_beat_synchronous() -> None:
    lib = MagicMock()
    lib.feature.chroma_stft.return_value = [[0.0]]
    lib.util.sync.return_value = [[0.0]]
    lib.segment.agglomerative.return_value = [0, 2]  # indices into beat segments
    beat_frames = [0, 100, 200, 300, 400]
    beat_times = [0.0, 5.0, 10.0, 15.0, 20.0]
    bounds = section_boundaries([0.0] * 1000, 22050, 30.0, beat_frames, beat_times, librosa_mod=lib)
    # boundary indices 0,2 -> beat_times[0]=0.0, beat_times[2]=10.0 (+ 0 and duration)
    assert 0.0 in bounds and 10.0 in bounds and 30.0 in bounds
    lib.util.sync.assert_called_once()  # clustered beat-synchronous chroma


def test_section_boundaries_fallback_when_few_beats() -> None:
    lib = MagicMock()
    lib.feature.chroma_stft.return_value = [[0.0]]
    lib.segment.agglomerative.return_value = [0, 300]
    lib.frames_to_time.return_value = [0.0, 15.0]
    bounds = section_boundaries([0.0] * 1000, 22050, 30.0, [0], [0.0], librosa_mod=lib)
    assert 0.0 in bounds and 15.0 in bounds and 30.0 in bounds
    lib.util.sync.assert_not_called()
