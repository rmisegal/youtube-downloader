"""Scaffold an editable segments JSON from ``--search`` candidates.

``--search`` lists candidate videos (title/url/duration); this turns that list into
a Video Content Matcher *segments* file — one scene per candidate with a 0:00 in-point
and a short default clip length — that the user (or the matcher) edits, then feeds to
``--fetch-movie`` / ``--build-movie``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULT_CLIP_SECONDS = 6


def candidates_to_segments(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map search candidates → an ordered segments list (start 0:00, short clip)."""
    out: list[dict[str, Any]] = []
    for i, cand in enumerate(candidates, start=1):
        out.append({
            "sequence_number": i,
            "requested_topic": cand.get("requested_topic", ""),
            "video_title": cand.get("video_title", ""),
            "video_url": cand.get("video_url", ""),
            "detection_method": "Visual Description",
            "start_time": "00:00:00",
            "duration_seconds": _DEFAULT_CLIP_SECONDS,
        })
    return out


def load_candidates(path: str) -> list[dict[str, Any]]:
    """Read + validate a ``--search`` candidates JSON (a list of candidate objects)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("candidates JSON must be a list of candidate objects")
    return data


def write_segments(segments: list[dict[str, Any]], out_path: str) -> str:
    """Write the segments list to ``out_path`` (UTF-8, pretty); return the path."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(segments, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path
