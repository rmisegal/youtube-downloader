"""Build a playlist from the Video Content Matcher segments JSON.

Each matched segment (sequence_number, video_url, start_time HH:MM:SS,
duration_seconds) becomes one ordered video member playing that exact in-point for
that long. The agent's download sub-agent saves each segment's video as
``seg_<sequence_number>.mp4`` in ``video_dir``; this references those files. With a
``leading_audio`` the clips contribute picture only (music score); otherwise they
keep their own audio (a narrated montage). The result is a v1.05 playlist the mixer
renders into ONE film.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def to_seconds(value: Any) -> float:
    """Parse ``HH:MM:SS`` / ``MM:SS`` / seconds into a float number of seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    parts = [float(p) for p in str(value).strip().split(":")] or [0.0]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[-3] * 3600 + parts[-2] * 60 + parts[-1]


def build_movie_playlist(
    segments: list[dict[str, Any]], video_dir: str, *,
    leading_audio: str | None = None, out_path: str | None = None,
    sync_target: str | None = None,
) -> str:
    """Write a playlist YAML for the matched segments; return its path.

    With ``sync_target`` AND ``leading_audio`` the scene cuts are **beat-synced** to
    the song (clips change on the bar); otherwise scenes play their ``play_time``.
    """
    ordered = sorted(segments, key=lambda s: s.get("sequence_number", 0))
    audio = "false" if leading_audio else "true"
    lines = [
        'version: "1.05"', "metadata:", f"  source_folder: '{video_dir}'",
        "  output: { display: true, save: true }",
        f"  mix: {{ video: true, audio: {audio} }}",
    ]
    if leading_audio:
        lines.append(f"  leading: {{ kind: audio, file: '{leading_audio}' }}")
        if sync_target:
            lines.append(f"  sync: {{ enabled: true, target: {sync_target}, mode: bar }}")
    lines += ["  loop: false", "members:"]
    for i, seg in enumerate(ordered, start=1):
        n = seg.get("sequence_number", i)
        start = to_seconds(seg.get("start_time", 0))
        play = float(seg.get("duration_seconds", 6) or 6)
        lines.append(f'  - {{ id: {i}, type: video, file: "seg_{n}.mp4", '
                     f"start_time: {start}, play_time: {play} }}")
    out = out_path or str(Path(video_dir) / "movie.yaml")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def load_segments(json_path: str) -> list[dict[str, Any]]:
    """Read + validate the matcher segments JSON (a list of segment objects)."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("segments JSON must be a list of segment objects")
    return data
