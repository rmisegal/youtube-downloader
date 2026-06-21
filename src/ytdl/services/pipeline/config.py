"""``MovieConfig`` — the wizard's output, the pipeline's single source of truth.

A typed, versioned config (GtaiGrader ``RunOptions`` pattern) round-tripped to
``config.json``. Its properties decide conditional pipeline behaviour: a leading song
turns on the STRUCTURE + beat-sync path; without one, scenes use a fixed length.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

CONFIG_VERSION = "1.06"


@dataclass
class MovieConfig:
    """All settings the pipeline needs (collected by the wizard or the agent)."""

    version: str = CONFIG_VERSION
    idea: str = ""
    topic: str = ""
    description: str = ""
    vibe: str = ""
    leading: str = ""            # leading audio path ("" → no soundtrack)
    # 0 = AUTO: one unique scene per music section (no repeats — the default). A
    # positive value CAPS the scene count (fewer searches, but clips will repeat).
    scene_target: int = 0
    sync_target: str = "video_art"
    mode: str = "bar"
    scene_seconds: float = 6.0   # per-scene length when there is no leading audio
    download_resolution: int = 720  # cap fetched footage (render is 720p) — avoids 4K bloat
    output_dir: str = ""
    llm_vendor: str = "claude"
    llm_auth: str = "cli"        # "cli" (default, CLI-login) or "api" (API key)

    @property
    def has_leading(self) -> bool:
        """True when a leading soundtrack drives structure + beat-sync."""
        return bool(self.leading)

    @property
    def stages(self) -> list[str]:
        """Ordered stage names to run (STRUCTURE only when a leading song exists)."""
        head = ["structure"] if self.has_leading else []
        return [*head, "script", "match", "fetch", "build", "render", "report"]

    def save(self, path: str) -> str:
        """Write the config to ``path`` as pretty JSON; return the path."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str) -> MovieConfig:
        """Load a config JSON, ignoring unknown keys (forward-compatible)."""
        data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})
