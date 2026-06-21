"""``StageState`` — file-on-disk pipeline progress for resume (GtaiGrader pattern).

Each completed stage is recorded in ``<build>/state.json``; the orchestrator skips a
stage that is already ``done`` AND whose artifact still exists. Delete ``state.json``
(or a stage's entry) to force a re-run.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Stages that leave a file artifact — used to detect a half-finished run.
_ARTIFACTS = {
    "structure": "structure.json",
    "script": "script.json",
    "match": "segments.json",
    "build": "videos/movie.yaml",
}


class StageState:
    """Track which pipeline stages have completed under a BUILD folder."""

    def __init__(self, build_dir: str) -> None:
        self._dir = Path(build_dir)
        self._path = self._dir / "state.json"
        self._data: dict[str, Any] = {}
        if self._path.exists():
            self._data = json.loads(self._path.read_text(encoding="utf-8"))

    def is_done(self, stage: str) -> bool:
        """True if ``stage`` is recorded done and its artifact (if any) still exists."""
        if self._data.get(stage, {}).get("status") != "done":
            return False
        art = _ARTIFACTS.get(stage)
        return art is None or (self._dir / art).exists()

    def mark_done(self, stage: str, **info: Any) -> None:
        """Record ``stage`` as completed (with optional info) and persist."""
        self._data[stage] = {"status": "done", **info}
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    def reset(self, stage: str) -> None:
        """Forget ``stage`` so it re-runs next time; persist."""
        if self._data.pop(stage, None) is not None:
            self._path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
