"""Assemble the analysis result + write JSON/CSV (PRD-beatsync §5).

``frame_index = round(timestamp_sec * target_fps)`` — the seconds→frame mapping
that lets an NLE place a cut on an exact frame. Pure functions, no DSP.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ytdl.constants import TIER_BAR, TIER_BEAT, TIER_PHRASE, TIER_SECTION

Result = dict[str, Any]


def _frame(t: float, fps: float) -> int:
    return round(t * fps)


def build_result(
    *, file_name: str, duration: float, bpm: float, fps: float, device: str,
    beats: Sequence[float], bars: Sequence[dict], phrases: Sequence[dict],
    sections: Sequence[dict], levels: Sequence[str], gpu_available: bool = False,
) -> Result:
    """Build the cut-point JSON object for the selected ``levels``."""
    cut: dict[str, Any] = {}
    if TIER_BEAT in levels:
        cut["beats"] = [
            {"timestamp_sec": round(b, 3), "frame_index": _frame(b, fps), "confidence": 0.9}
            for b in beats
        ]
    if TIER_BAR in levels:
        cut["bars"] = [
            {"timestamp_sec": round(x["timestamp_sec"], 3),
             "frame_index": _frame(x["timestamp_sec"], fps), "bar_index": x["bar_index"]}
            for x in bars
        ]
    if TIER_PHRASE in levels:
        cut["phrases"] = [
            {"timestamp_sec": round(p["timestamp_sec"], 3),
             "frame_index": _frame(p["timestamp_sec"], fps), "phrase_type": p["phrase_type"]}
            for p in phrases
        ]
    if TIER_SECTION in levels:
        cut["sections"] = list(sections)
    return {
        "metadata": {
            "file_name": file_name, "duration_seconds": round(duration, 3),
            "global_bpm": round(bpm, 1), "target_fps": fps, "device": device,
            "gpu_available": gpu_available,
        },
        "cut_points": cut,
    }


def write_json(result: Result, out_path: str) -> str:
    """Write ``result`` as pretty JSON; return the path."""
    Path(out_path).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def write_csv(result: Result, out_path: str) -> str:
    """Flatten every cut-point into ``tier,timestamp_sec,frame_index,extra`` rows."""
    rows = [("tier", "timestamp_sec", "frame_index", "extra")]
    for tier, items in result.get("cut_points", {}).items():
        for it in items:
            ts = it.get("timestamp_sec", it.get("start_sec", 0.0))
            extra = it.get("label") or it.get("phrase_type") or it.get("bar_index") or ""
            rows.append((tier, ts, it.get("frame_index", ""), extra))
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerows(rows)
    return out_path
