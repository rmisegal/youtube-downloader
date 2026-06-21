"""Music-sync pre-pass (PRD-beatsync §6): place members on planned cut-points.

When ``metadata.sync.enabled`` and the leading track is AUDIO, the leading song is
analyzed and the :func:`plan_cuts` planner — driven by the playlist's CONTENT TARGET
profile (Video Art / DJ Party / Lecture / …) and the track's mood — produces the
cut-points and a per-cut transition. Each image/video member is placed at a cut-point
with the planner's transition and the track BPM (so beat-reactive effects throb in
time). The placed members then render through the existing concat/timeline renderer.
No runtime LLM is involved — the pacing/transition matrix is a hardcoded lookup table.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ytdl.constants import LEADING_AUDIO
from ytdl.services.analysis.analyzer import AudioAnalyzer
from ytdl.services.analysis.cut_planner import plan_cuts
from ytdl.services.analysis.profiles import DEFAULT_TARGET, get_profile, mood_from_bpm


def prepare_render(
    playlist: Any, segments: list[Any], config: Any, *, analyzer: Any = None
) -> tuple[list[Any], float, dict | None]:
    """Return ``(synced_segments, dissolve_seconds, overlay_payload)`` for the renderer."""
    segments = apply_sync(playlist, segments, config, analyzer=analyzer)
    dissolve = playlist.sync_crossfade() if playlist.sync_enabled() else 0.0
    return segments, dissolve, build_overlay(playlist, config, analyzer=analyzer)


def build_overlay(playlist: Any, config: Any, *, analyzer: Any = None) -> dict | None:
    """Analyze the leading track and bundle the overlay-track elements + beat grid.

    Returns ``None`` when there are no overlay tracks or no leading audio (beat-timed
    text needs the leading track's beat grid).
    """
    tracks = playlist.metadata.tracks
    meta = playlist.metadata
    if tracks.is_empty() or meta.leading_kind() != LEADING_AUDIO or not meta.leading_file():
        return None
    result = (analyzer or AudioAnalyzer(config)).analyze(meta.leading_file())
    return {
        "elements": tracks.all_elements(),
        "beats": [b["timestamp_sec"] for b in result["cut_points"].get("beats", [])],
        "bpm": result["metadata"]["global_bpm"],
        "total": result["metadata"]["duration_seconds"],
    }


def apply_sync(playlist: Any, segments: list[Any], config: Any, *, analyzer: Any = None) -> list[Any]:
    """Entry point: return sync-placed segments, or ``segments`` unchanged."""
    meta = playlist.metadata
    if not meta.sync_enabled() or not segments:
        return segments
    if meta.leading_kind() != LEADING_AUDIO or not meta.leading_file():
        return segments  # sync needs an audio soundtrack to follow
    return sync_segments(
        segments, meta.leading_file(), config, mode=meta.sync_mode(),
        target=meta.sync_target(), crossfade=meta.sync_crossfade(), analyzer=analyzer,
    )


def sync_segments(
    segments: list[Any], leading_file: str, config: Any, *, mode: str = "auto",
    target: str | None = None, crossfade: float = 0.0, analyzer: Any = None,
) -> list[Any]:
    """Analyze the leading audio, plan cut-points from the target profile, place members."""
    get = config.get if config is not None else (lambda _k, default=None: default)
    analyzer = analyzer or AudioAnalyzer(config)
    result = analyzer.analyze(leading_file)
    bpm = result["metadata"]["global_bpm"]
    total = result["metadata"]["duration_seconds"]
    profile = get_profile(target or get("analysis.default_target", DEFAULT_TARGET))
    # Crossfade mode dissolves every junction, so suppress the section-change black.
    cuts = plan_cuts(result["cut_points"], profile, mood=mood_from_bpm(bpm),
                     mode=mode, no_black=crossfade > 0)
    return place_on_cuts(segments, cuts, total, bpm)


def place_on_cuts(segments: list[Any], cuts: list[dict], total: float, bpm: float) -> list[Any]:
    """Place members (cycling) on each cut slot; use the cut's pre-selected transition."""
    placed = sorted(
        (c for c in cuts if 0 <= c["timestamp_sec"] < total),
        key=lambda c: c["timestamp_sec"],
    )
    if not placed:
        return segments
    out: list[Any] = []
    for i, cut in enumerate(placed):
        start = cut["timestamp_sec"]
        end = placed[i + 1]["timestamp_sec"] if i + 1 < len(placed) else total
        if end <= start:
            continue
        seg = segments[i % len(segments)]
        out.append(replace(
            seg, at=start, until=end, play_seconds=end - start,
            transition=cut["transition"], bpm=bpm,
        ))
    return out
