"""Unit tests for :mod:`ytdl.infra.playback.duration` (mocked subprocess)."""

from __future__ import annotations

from types import SimpleNamespace

from ytdl.infra.playback.duration import probe_duration, probe_media


def _runner(stderr: str):
    calls: list[list[str]] = []

    def run(cmd, **_kwargs):
        calls.append(cmd)
        return SimpleNamespace(stderr=stderr)

    return run, calls


def test_parses_duration_seconds() -> None:
    run, calls = _runner("  Duration: 00:01:40.50, start: 0.0\n")
    assert probe_duration("clip.mp4", "ffmpeg", runner=run) == 100.5
    assert calls == [["ffmpeg", "-i", "clip.mp4"]]


def test_parses_hours() -> None:
    run, _ = _runner("Duration: 01:02:03.00,")
    assert probe_duration("x.mkv", "ffmpeg", runner=run) == 3723.0


def test_no_match_returns_zero() -> None:
    run, _ = _runner("no duration here")
    assert probe_duration("x.mp4", "ffmpeg", runner=run) == 0.0


def test_missing_stderr_returns_zero() -> None:
    def run(_cmd, **_kwargs):
        return SimpleNamespace(stderr=None)

    assert probe_duration("x.mp4", "ffmpeg", runner=run) == 0.0


def test_probe_media_detects_audio_and_duration() -> None:
    stderr = "  Duration: 00:00:30.00,\n  Stream #0:1: Audio: aac, 48000 Hz\n"
    run, calls = _runner(stderr)
    duration, has_audio = probe_media("clip.mp4", "ffmpeg", runner=run)
    assert duration == 30.0
    assert has_audio is True
    assert calls == [["ffmpeg", "-i", "clip.mp4"]]


def test_probe_media_no_audio_stream() -> None:
    run, _ = _runner("  Duration: 00:00:10.00,\n  Stream #0:0: Video: av1\n")
    duration, has_audio = probe_media("silent.mkv", "ffmpeg", runner=run)
    assert duration == 10.0
    assert has_audio is False


def test_probe_media_missing_stderr() -> None:
    def run(_cmd, **_kwargs):
        return SimpleNamespace(stderr=None)

    assert probe_media("x.mp4", "ffmpeg", runner=run) == (0.0, False)
