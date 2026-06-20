"""Unit tests for bars/phrases derivation (pure logic)."""

from __future__ import annotations

from ytdl.services.analysis.grid import build_bars, build_phrases


def test_build_bars_groups_by_meter() -> None:
    beats = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    bars = build_bars(beats, onsets=[0.0, 2.0], meter=4)
    assert [b["bar_index"] for b in bars] == [1, 2]
    assert bars[0]["timestamp_sec"] == 0.0
    assert bars[1]["timestamp_sec"] == 2.0


def test_downbeat_accent_picks_strongest_onset() -> None:
    beats = [0.0, 0.5, 1.0, 1.5]
    bars = build_bars(beats, onsets=[1.0], meter=4)  # accent on the 3rd beat
    assert bars[0]["accent_sec"] == 1.0


def test_build_phrases_groups_bars() -> None:
    bars = [{"timestamp_sec": float(i), "bar_index": i + 1} for i in range(16)]
    phrases = build_phrases(bars, phrase_bars=8)
    assert len(phrases) == 2
    assert phrases[0]["phrase_type"] == "Phrase_A_Start"
    assert "Transition" in phrases[1]["phrase_type"]
    assert phrases[1]["timestamp_sec"] == 8.0


def test_empty_inputs() -> None:
    assert build_bars([], [], meter=4) == []
    assert build_phrases([], phrase_bars=8) == []
