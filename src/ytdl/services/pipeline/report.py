"""REPORT stage — a plain-language markdown summary of a pipeline run (GtaiGrader style)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_report(build_dir: str, config: Any, stats: dict[str, Any]) -> str:
    """Write ``pipeline_report.md`` summarising the run; return its path."""
    lines = [
        "# Movie pipeline report", "",
        f"- topic: {config.topic}",
        f"- vibe: {config.vibe}",
        f"- leading audio: {config.leading or '(none)'}",
        f"- beat-sync: {config.sync_target}/{config.mode}" if config.has_leading else "- beat-sync: (off)",
        f"- scenes planned: {stats.get('scenes', 0)}",
        f"- scenes matched: {stats.get('matched', 0)}",
        f"- videos downloaded: {stats.get('downloaded', 0)}",
        f"- failed downloads: {stats.get('failed', 0)}",
        f"- playlist: {stats.get('playlist', '')}",
        f"- output video: {stats.get('output', '')}",
        "",
    ]
    out = str(Path(build_dir) / "pipeline_report.md")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(lines), encoding="utf-8")
    return out
