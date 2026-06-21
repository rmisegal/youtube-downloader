"""Clean, log-friendly download progress for yt-dlp (a ``progress_hooks`` callback).

yt-dlp's native bar uses carriage returns that vanish in captured logs / background
runs. This prints a plain newline line at 0/20/40/60/80 % and on completion, so the
user sees progress whether the download runs in a terminal OR in a background task.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any


def _name(d: dict[str, Any]) -> str:
    return (d.get("filename") or d.get("info_dict", {}).get("title") or "").replace("\\", "/").split("/")[-1]


def _mb(num: Any) -> str:
    try:
        return f"{float(num) / 1_048_576:.1f}MB"
    except (TypeError, ValueError):
        return "?"


def make_progress_hook(out: Any = None) -> Callable[[dict[str, Any]], None]:
    """Return a yt-dlp progress hook printing a line every ~20 % (and on finish)."""
    out = out or sys.stderr
    state = {"step": -1}

    def hook(d: dict[str, Any]) -> None:
        status = d.get("status")
        if status == "finished":
            print(f"[download] {_name(d)}: done ({_mb(d.get('total_bytes') or d.get('downloaded_bytes'))})",
                  file=out, flush=True)
            state["step"] = -1
            return
        if status != "downloading":
            return
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
        pct = int((d.get("downloaded_bytes") or 0) * 100 / total) if total else 0
        step = pct // 20
        if step <= state["step"]:
            return
        state["step"] = step
        print(f"[download] {_name(d)}: {pct:3d}%  {d.get('_speed_str', '').strip()}  "
              f"ETA {d.get('_eta_str', '').strip()}", file=out, flush=True)

    return hook
