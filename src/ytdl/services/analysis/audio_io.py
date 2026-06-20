"""Load audio fast: pre-decode to mono WAV via the bundled ffmpeg, then librosa.

``librosa.load`` on an mp3 is slow (~25s/3min: audioread decode + resample). We
first decode to a mono WAV at the analysis sample rate with the bundled ffmpeg
(~0.5s, reuses :class:`FfmpegLocator`), then load the WAV (instant). Subprocess +
librosa are injectable so tests never touch real audio.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ytdl.infra.ffmpeg import FfmpegLocator
from ytdl.shared.errors import AudioAnalysisError


def load_audio(
    path: str,
    *,
    sample_rate: int = 22050,
    ffmpeg: FfmpegLocator | None = None,
    runner: Callable[..., Any] = subprocess.run,
    librosa_mod: Any = None,
) -> tuple[Any, int]:
    """Return ``(samples, sample_rate)`` for ``path`` (mono, at ``sample_rate``)."""
    if not Path(path).is_file():
        raise AudioAnalysisError(f"Audio file not found: {path}")
    ffmpeg = ffmpeg or FfmpegLocator()
    tmp_dir = tempfile.mkdtemp(prefix="ytdl_bs_")
    wav = str(Path(tmp_dir) / "audio.wav")
    try:
        runner(
            [ffmpeg.exe(), "-nostdin", "-y", "-i", str(path),
             "-ac", "1", "-ar", str(sample_rate), wav],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if not Path(wav).is_file():
            raise AudioAnalysisError(f"Could not decode audio (ffmpeg produced nothing): {path}")
        if librosa_mod is None:
            import librosa as librosa_mod  # noqa: PLC0415 - lazy heavy import
        samples, sr = librosa_mod.load(wav, sr=sample_rate)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    if samples is None or len(samples) == 0:
        raise AudioAnalysisError(f"Empty/unreadable audio: {path}")
    return samples, int(sr)
