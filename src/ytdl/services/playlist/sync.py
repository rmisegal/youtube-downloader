"""Music-sync pre-pass (PRD-beatsync §6): place members on planned cut-points.

When ``metadata.sync.enabled`` and the leading track is AUDIO, the leading song is
analyzed, the :func:`plan_cuts` planner picks cut-points (section-driven in ``auto``
mode), and each image/video member is placed at a cut-point with its transition
FITTED to that sync type — a beat-reactive effect (pulse/shake) on energetic beat
cuts, a slow zoom on phrase cuts, etc. The placed members then render through the
existing timeline compositor (no new render code). Reuses AudioAnalyzer + CutPlanner.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ytdl.constants import LEADING_AUDIO
from ytdl.services.analysis.analyzer import AudioAnalyzer
from ytdl.services.analysis.cut_planner import plan_cuts


def apply_sync(playlist: Any, segments: list[Any], config: Any, *, analyzer: Any = None) -> list[Any]:
    """Entry point: return sync-placed segments, or ``segments`` unchanged."""
    meta = playlist.metadata
    if not meta.sync_enabled() or not segments:
        return segments
    if meta.leading_kind() != LEADING_AUDIO or not meta.leading_file():
        return segments  # sync needs an audio soundtrack to follow
    return sync_segments(
        segments, meta.leading_file(), config, mode=meta.sync_mode(), analyzer=analyzer
    )


def sync_segments(
    segments: list[Any], leading_file: str, config: Any, *, mode: str = "auto",
    analyzer: Any = None,
) -> list[Any]:
    """Analyze the leading audio, plan cut-points, and place members."""
    get = config.get if config is not None else (lambda _k, default=None: default)
    analyzer = analyzer or AudioAnalyzer(config)
    result = analyzer.analyze(leading_file)
    plan = plan_cuts(
        result["cut_points"], mode=mode,
        section_rules=get("analysis.section_rules", None),
        fill_on_phrase_end=get("analysis.fill_on_phrase_end", True),
    )
    return place_on_cuts(
        segments, plan, result["metadata"]["duration_seconds"],
        result["metadata"]["global_bpm"],
        tier_map=get("analysis.tier_transitions", {}),
        section_map=get("analysis.section_transitions", {}),
    )


def place_on_cuts(
    segments: list[Any], plan: list[dict], total: float, bpm: float, *,
    tier_map: dict | None = None, section_map: dict | None = None,
) -> list[Any]:
    """Place members (cycling) on each cut slot; fit the transition to the tier."""
    tier_map, section_map = tier_map or {}, section_map or {}
    cuts = sorted(
        (c for c in plan if 0 <= c["timestamp_sec"] < total),
        key=lambda c: c["timestamp_sec"],
    )
    if not cuts:
        return segments
    out: list[Any] = []
    for i, cut in enumerate(cuts):
        start = cut["timestamp_sec"]
        end = cuts[i + 1]["timestamp_sec"] if i + 1 < len(cuts) else total
        if end <= start:
            continue
        seg = segments[i % len(segments)]
        trans = section_map.get(cut["section"]) or tier_map.get(cut["tier"]) or seg.transition
        out.append(replace(
            seg, at=start, until=end, play_seconds=end - start, transition=trans, bpm=bpm,
        ))
    return out
