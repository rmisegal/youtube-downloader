"""Turn an audio analysis into a scenario grid (STRUCTURE stage).

The leading song is analysed once (``AudioAnalyzer``); this samples ``target`` cut
points evenly across its **bars** (the musical 4/4 grid) and emits one scenario slot
per cut — each with its in/out seconds and the section it falls in (intro/verse/
chorus/…). Fewer bars than ``target`` → fewer (but never zero) slots. No bars (no
leading song) → an even split of ``total`` into ``target`` fixed slots.
"""

from __future__ import annotations

from typing import Any

from ytdl.services.analysis.cut_planner import plan_cuts
from ytdl.services.analysis.profiles import get_profile, mood_from_bpm


def _section_at(t: float, sections: list[dict[str, Any]]) -> str:
    """Label of the section containing time ``t`` (last section that started by ``t``)."""
    label = ""
    for sec in sections:
        if float(sec.get("start_sec", sec.get("timestamp_sec", 0.0))) <= t:
            label = sec.get("label", "") or label
    return label or "section"


def _even_indices(count: int, picks: int) -> list[int]:
    """``picks`` indices spread evenly across ``range(count)`` (inclusive of ends)."""
    if picks <= 1 or count <= 1:
        return [0]
    return sorted({round(i * (count - 1) / (picks - 1)) for i in range(picks)})


def _slots_from_times(times: list[float], total: float, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build scene slots from ordered cut times (each slot spans to the next cut)."""
    ordered = sorted(t for t in times if 0 <= t < total)
    slots: list[dict[str, Any]] = []
    for i, at in enumerate(ordered):
        until = ordered[i + 1] if i + 1 < len(ordered) else (total or at + 6.0)
        if until <= at:
            continue
        slots.append({
            "index": len(slots) + 1, "at": round(at, 3), "until": round(until, 3),
            "duration": round(until - at, 3), "section": _section_at(at, sections),
        })
    return slots


def grid_from_cuts(analysis: dict[str, Any], sync_target: str, mode: str) -> list[dict[str, Any]]:
    """One scene per SYNC cut — uses the SAME ``plan_cuts`` the build will, so the
    scene count equals the beat-slot count → every music section gets its OWN clip
    (no cycling/duplication)."""
    cut = analysis.get("cut_points", {})
    total = float(analysis.get("metadata", {}).get("duration_seconds", 0.0))
    bpm = float(analysis.get("metadata", {}).get("global_bpm", 120.0))
    cuts = plan_cuts(cut, get_profile(sync_target), mood=mood_from_bpm(bpm), mode=mode)
    return _slots_from_times([c["timestamp_sec"] for c in cuts], total, list(cut.get("sections", [])))


def build_scenario_grid(analysis: dict[str, Any], target: int) -> list[dict[str, Any]]:
    """Return ``target`` (or fewer) scenario slots from an analyze() result."""
    target = max(1, target)
    cut = analysis.get("cut_points", {})
    total = float(analysis.get("metadata", {}).get("duration_seconds", 0.0))
    bars = [float(b["timestamp_sec"]) for b in cut.get("bars", []) if "timestamp_sec" in b]
    sections = list(cut.get("sections", []))
    if not bars:  # no leading song / no bar grid → even fixed split
        bars = [round(total * i / target, 3) for i in range(target)] or [0.0]
    picks = [bars[i] for i in _even_indices(len(bars), min(target, len(bars)))]
    slots: list[dict[str, Any]] = []
    for i, at in enumerate(picks):
        until = picks[i + 1] if i + 1 < len(picks) else (total or at + 6.0)
        slots.append({
            "index": i + 1, "at": round(at, 3), "until": round(until, 3),
            "duration": round(max(0.1, until - at), 3), "section": _section_at(at, sections),
        })
    return slots
