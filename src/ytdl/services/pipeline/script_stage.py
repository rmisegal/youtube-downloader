"""SCRIPT stage — turn topic/vibe + the scenario grid into N scene descriptions.

An LLM (any :class:`LlmProvider`) is asked to write, for each music-cued scene slot, a
``visual_description`` and a ``search_query`` (a YouTube query to find real footage).
The reply is aligned back onto the grid so the output is always exactly one scene per
slot — even if the model returns sloppy JSON. The agent path may instead write
``script.json`` directly; this is the standalone (provider) path.
"""

from __future__ import annotations

import json
from typing import Any

from ytdl.shared.errors import LlmError

_SYSTEM = ("You are a music-video director. Plan scenes that can be filled with REAL "
           "YouTube footage (no fabricated imagery). Output STRICT JSON only.")


def build_prompt(config: Any, grid: list[dict[str, Any]]) -> str:
    """Compose the director prompt from the config + the scenario grid."""
    lines = [
        f"Topic: {config.topic}", f"Description: {config.description}", f"Vibe: {config.vibe}",
        f"Plan {len(grid)} sequential scenes for a music video. For EACH scene give an object with",
        '"visual_description" (what is on screen) and "search_query" (a YouTube search for real footage).',
        "Scenes (section + length in seconds):",
    ]
    lines += [f"  scene {s['index']}: section={s.get('section', '')} length={s['duration']}s" for s in grid]
    lines.append("Return ONLY a JSON array of the scene objects, in order.")
    return "\n".join(lines)


def _extract_array(text: str) -> list[Any]:
    """Pull the first JSON array out of a model reply (tolerates prose / code fences)."""
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        raise LlmError("script: model reply contained no JSON array")
    return json.loads(text[start:end + 1])


def align_to_grid(raw: list[Any], grid: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One scene per slot; pull description/query from ``raw`` by index, fill gaps."""
    out: list[dict[str, Any]] = []
    for i, slot in enumerate(grid):
        item = raw[i] if i < len(raw) and isinstance(raw[i], dict) else {}
        desc = item.get("visual_description") or item.get("description") or ""
        query = item.get("search_query") or item.get("query") or desc or slot.get("section", "")
        out.append({
            "scenario_number": slot["index"], "section": slot.get("section", ""),
            "start_sec": slot["at"], "duration_sec": slot["duration"],
            "visual_description": desc, "search_query": query,
        })
    return out


def generate_script(provider: Any, config: Any, grid: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ask ``provider`` for the script and align it to the grid (provider path)."""
    return align_to_grid(_extract_array(provider.complete(build_prompt(config, grid), system=_SYSTEM)), grid)
