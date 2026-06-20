"""Unit tests for audio_io.load_audio + beats.extract_beats (mocked ffmpeg/librosa)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ytdl.services.analysis.audio_io import load_audio
from ytdl.services.analysis.beats import extract_beats
from ytdl.shared.errors import AudioAnalysisError


def _ffmpeg() -> MagicMock:
    ff = MagicMock()
    ff.exe.return_value = "/fake/ffmpeg"
    return ff


def test_load_audio_missing_file_raises() -> None:
    with pytest.raises(AudioAnalysisError):
        load_audio("nope.mp3")


def test_load_audio_decodes_then_loads_wav(tmp_path) -> None:
    src = tmp_path / "song.mp3"
    src.write_bytes(b"x")

    def runner(cmd, **_kw):
        open(cmd[-1], "w").close()  # ffmpeg "produces" the wav (last argv)
        return MagicMock()

    lib = MagicMock()
    lib.load.return_value = ([0.1, 0.2, 0.3], 22050)
    samples, sr = load_audio(str(src), ffmpeg=_ffmpeg(), runner=runner, librosa_mod=lib)
    assert sr == 22050 and len(samples) == 3
    assert lib.load.call_args.args[0].endswith("audio.wav")  # loaded the decoded wav


def test_load_audio_decode_failure_raises(tmp_path) -> None:
    src = tmp_path / "song.mp3"
    src.write_bytes(b"x")
    with pytest.raises(AudioAnalysisError):  # runner does not create the wav
        load_audio(str(src), ffmpeg=_ffmpeg(), runner=lambda *a, **k: MagicMock(),
                   librosa_mod=MagicMock())


def test_load_audio_empty_raises(tmp_path) -> None:
    src = tmp_path / "s.mp3"
    src.write_bytes(b"x")

    def runner(cmd, **_kw):
        open(cmd[-1], "w").close()
        return MagicMock()

    lib = MagicMock()
    lib.load.return_value = ([], 22050)
    with pytest.raises(AudioAnalysisError):
        load_audio(str(src), ffmpeg=_ffmpeg(), runner=runner, librosa_mod=lib)


def test_extract_beats_maps_arrays_to_seconds() -> None:
    lib = MagicMock()
    lib.onset.onset_strength.return_value = [0.1, 0.2]
    lib.beat.beat_track.return_value = (120.0, [10, 20, 30])
    lib.onset.onset_detect.return_value = [5, 15]
    lib.frames_to_time.side_effect = lambda frames, sr: [f * 0.05 for f in frames]
    r = extract_beats([0.0] * 100, 22050, librosa_mod=lib)
    assert r["bpm"] == 120.0
    assert r["beats"] == [0.5, 1.0, 1.5]
    assert r["beat_frames"] == [10, 20, 30]
    assert r["onsets"] == [0.25, 0.75]
    assert r["sr"] == 22050
    lib.onset.onset_strength.assert_called_once()  # computed once, fed to both
    assert "onset_envelope" in lib.beat.beat_track.call_args.kwargs
