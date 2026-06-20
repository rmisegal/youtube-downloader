"""Analyze-and-export helper (keeps the SDK method a thin one-liner)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ytdl.services.analysis.analyzer import AudioAnalyzer
from ytdl.services.analysis.export import write_csv, write_json


def analyze_and_export(
    config: Any,
    audio_path: str,
    *,
    levels: Sequence[str] | None = None,
    target_fps: float | None = None,
    out_path: str | None = None,
    fmt: str = "json",
) -> dict[str, Any]:
    """Analyze ``audio_path`` and optionally write JSON/CSV; return the result."""
    result = AudioAnalyzer(config).analyze(audio_path, levels=levels, target_fps=target_fps)
    if out_path:
        (write_csv if fmt == "csv" else write_json)(result, out_path)
        result = {**result, "output": out_path}
    return result
