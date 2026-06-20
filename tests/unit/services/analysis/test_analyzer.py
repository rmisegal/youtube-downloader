"""Unit tests for AudioAnalyzer orchestration (sub-steps patched)."""

from __future__ import annotations

from ytdl.services.analysis import analyzer as mod
from ytdl.shared.config import ConfigManager


def _cfg() -> ConfigManager:
    return ConfigManager(data={
        "version": "1.05",
        "analysis": {
            "default_fps": 30, "default_levels": ["beat", "bar", "phrase", "section"],
            "meter": 4, "phrase_bars": 8, "use_gpu": "off",
        },
    })


def test_analyze_orchestrates_all_tiers(monkeypatch) -> None:
    monkeypatch.setattr(mod, "resolve_device", lambda *a, **k: "cpu")
    monkeypatch.setattr(mod, "load_audio", lambda *a, **k: ([0.0] * 22050, 22050))  # 1s
    monkeypatch.setattr(mod, "extract_beats", lambda *a, **k: {
        "bpm": 128.0, "beats": [0.5, 1.0], "beat_frames": [10, 20], "onsets": [0.5], "sr": 22050})
    monkeypatch.setattr(mod, "extract_sections", lambda *a, **k: [
        {"start_sec": 0.0, "end_sec": 1.0, "label": "Intro"}])

    out = mod.AudioAnalyzer(_cfg()).analyze("song.mp3", target_fps=30)
    assert out["metadata"]["global_bpm"] == 128.0
    assert out["metadata"]["device"] == "cpu"
    assert out["metadata"]["target_fps"] == 30.0
    assert out["metadata"]["file_name"] == "song.mp3"
    assert len(out["cut_points"]["beats"]) == 2
    assert out["cut_points"]["beats"][0]["frame_index"] == 15  # 0.5 * 30
    assert out["cut_points"]["sections"][0]["label"] == "Intro"
    assert out["cut_points"]["bars"][0]["bar_index"] == 1


def test_analyze_honors_selected_levels(monkeypatch) -> None:
    monkeypatch.setattr(mod, "resolve_device", lambda *a, **k: "cpu")
    monkeypatch.setattr(mod, "load_audio", lambda *a, **k: ([0.0] * 100, 100))
    monkeypatch.setattr(mod, "extract_beats", lambda *a, **k: {
        "bpm": 100.0, "beats": [0.1], "beat_frames": [5], "onsets": [], "sr": 100})
    monkeypatch.setattr(mod, "extract_sections", lambda *a, **k: [])
    out = mod.AudioAnalyzer(_cfg()).analyze("s.mp3", levels=["beat"])
    assert set(out["cut_points"]) == {"beats"}
