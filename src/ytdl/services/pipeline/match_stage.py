"""MATCH stage — find the best YouTube section for each scene (Video Content Matcher).

For every scene the script's ``search_query`` is searched (rate-limited ``SDK.search``);
the best candidate (long enough for the scene, else the longest) is turned into a
segment with an in-point. Each result is cached to ``scenarios/scn_<n>.json`` so a
re-run resumes without re-searching. The merged list is the ``segments.json`` the
builder consumes; the same video may legitimately serve more than one scene.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

SearchFn = Callable[[str, int], list[dict[str, Any]]]


def _pick(candidates: list[dict[str, Any]], need_sec: float) -> dict[str, Any] | None:
    """Pick the SHORTEST candidate that is still ≥ ``need_sec`` (least to download);
    if none is long enough, fall back to the longest available. Avoids grabbing
    hour-long compilations to use a few seconds."""
    if not candidates:
        return None
    long_enough = [c for c in candidates if (c.get("duration_seconds") or 0) >= need_sec]
    if long_enough:
        return min(long_enough, key=lambda c: c.get("duration_seconds") or 0)
    return max(candidates, key=lambda c: c.get("duration_seconds") or 0)


def _start_hms(source_sec: int, need_sec: float) -> str:
    """A mid in-point (HH:MM:SS) that leaves room for a ``need_sec`` clip."""
    start = 0
    if source_sec > need_sec + 4:
        start = min(int(source_sec * 0.3), int(source_sec - need_sec - 2))
    return f"{start // 3600:02d}:{(start % 3600) // 60:02d}:{start % 60:02d}"


def match_one(search_fn: SearchFn, scene: dict[str, Any], results: int) -> dict[str, Any] | None:
    """Search the scene's query and build one segment, or None if nothing matched."""
    pick = _pick(search_fn(scene["search_query"], results), scene["duration_sec"])
    if not pick:
        return None
    return {
        "sequence_number": scene["scenario_number"], "requested_topic": scene["search_query"],
        "video_title": pick.get("video_title", ""), "video_url": pick.get("video_url", ""),
        "detection_method": "Visual Description",
        "start_time": _start_hms(int(pick.get("duration_seconds") or 0), scene["duration_sec"]),
        "duration_seconds": round(scene["duration_sec"], 3),
    }


def match_scenes(
    search_fn: SearchFn, script: list[dict[str, Any]], build_dir: str, *, results: int = 6,
) -> list[dict[str, Any]]:
    """Match every scene → segments, caching each to ``scenarios/`` (resumable)."""
    scn_dir = Path(build_dir) / "scenarios"
    scn_dir.mkdir(parents=True, exist_ok=True)
    segments: list[dict[str, Any]] = []
    for scene in script:
        cache = scn_dir / f"scn_{scene['scenario_number']}.json"
        if cache.exists():
            segments.append(json.loads(cache.read_text(encoding="utf-8")))
            continue
        seg = match_one(search_fn, scene, results)
        if seg:
            cache.write_text(json.dumps(seg, indent=2, ensure_ascii=False), encoding="utf-8")
            segments.append(seg)
    return segments
