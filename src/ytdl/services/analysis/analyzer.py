"""AudioAnalyzer — orchestrate the 4 tiers into one cut-point result.

Wires audio load (ffmpeg-predecode) → beats/onsets/tempo → bars/phrases →
sections, then assembles the JSON result. Config-driven (``analysis.*``); the
device (cpu/gpu) is resolved from ``analysis.use_gpu`` and recorded in metadata.
All collaborators are module-level functions so tests patch them.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ytdl.constants import ANALYSIS_TIERS
from ytdl.services.analysis.audio_io import load_audio
from ytdl.services.analysis.beats import extract_beats
from ytdl.services.analysis.export import build_result
from ytdl.services.analysis.gpu import resolve_device
from ytdl.services.analysis.grid import build_bars, build_phrases
from ytdl.services.analysis.structure import extract_sections


class AudioAnalyzer:
    """Extract multi-tier rhythm/structure cut-points from an audio file."""

    def __init__(
        self,
        config: Any = None,
        *,
        librosa_mod: Any = None,
        runner: Callable[..., Any] = subprocess.run,
        ffmpeg: Any = None,
    ) -> None:
        get = config.get if config is not None else (lambda _k, default=None: default)
        self._sr = get("analysis.sample_rate", 22050)
        self._meter = get("analysis.meter", 4)
        self._phrase_bars = get("analysis.phrase_bars", 8)
        self._default_fps = get("analysis.default_fps", 30)
        self._default_levels = get("analysis.default_levels", list(ANALYSIS_TIERS))
        self._use_gpu = get("analysis.use_gpu", "auto")
        self._librosa = librosa_mod
        self._runner = runner
        self._ffmpeg = ffmpeg

    def analyze(
        self, audio_path: str, *, levels: Sequence[str] | None = None,
        target_fps: float | None = None,
    ) -> dict[str, Any]:
        """Run all requested tiers; return the cut-point JSON result."""
        levels = list(levels) if levels else list(self._default_levels)
        fps = float(target_fps) if target_fps else float(self._default_fps)
        # librosa (the only installed backend) computes on the CPU, and the
        # ffmpeg-predecode keeps that under the <10s NFR. ``resolve_device`` enables
        # the shared cuda_libs and reports whether a GPU is available for an optional
        # neural backend — but the actual compute device here is always CPU.
        gpu_available = resolve_device(self._use_gpu, runner=self._runner) == "gpu"
        samples, sr = load_audio(
            audio_path, sample_rate=self._sr, ffmpeg=self._ffmpeg,
            runner=self._runner, librosa_mod=self._librosa,
        )
        duration = len(samples) / sr
        beats = extract_beats(samples, sr, librosa_mod=self._librosa)
        bars = build_bars(beats["beats"], beats["onsets"], meter=self._meter)
        phrases = build_phrases(bars, phrase_bars=self._phrase_bars)
        sections = extract_sections(
            samples, sr, duration, beats["beat_frames"], beats["beats"],
            beats["onsets"], librosa_mod=self._librosa,
        )
        return build_result(
            file_name=Path(audio_path).name, duration=duration, bpm=beats["bpm"],
            fps=fps, device="cpu", gpu_available=gpu_available, beats=beats["beats"],
            bars=bars, phrases=phrases, sections=sections, levels=levels,
        )
