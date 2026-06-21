"""``MovieWizard`` — collect a :class:`MovieConfig` interactively (Software/Skill/Agent).

Asks the setup questions in the order the user wanted: leading song + render settings
FIRST, then (once the song's structure can be summarised) the topic / description /
vibe that drive the script. I/O flows through an injected :class:`Prompter`, so the
same flow is unit-testable and the agent can collect the same fields another way.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from pathlib import Path

from ytdl.services.pipeline.config import MovieConfig
from ytdl.services.pipeline.prompter import Prompter

SYNC_TARGETS = ("video_art", "dj_party", "homemade_video", "presentation",
                "podcast", "road_travel", "topic_summary", "lecture")
MODES = ("bar", "half", "phrase")
VENDORS = ("claude", "gemini")
AUTHS = ("cli", "api")


class MovieWizard:
    """Build a MovieConfig from interactive prompts (optionally previewing the song)."""

    def __init__(self, prompter: Prompter, *, analyze_fn: Callable[[str], str] | None = None) -> None:
        self._p = prompter
        self._analyze = analyze_fn

    def run(self) -> MovieConfig:
        """Run the question flow and return the assembled config."""
        p = self._p
        cfg = MovieConfig()
        p.say("=== Movie pipeline setup ===")
        cfg.idea = p.ask("One-line movie idea")
        cfg.leading = p.ask_path("Leading audio file (blank = no soundtrack)")
        cfg.output_dir = p.ask_path("Output folder", default=str(Path.home() / "movies"))
        cfg.scene_target = p.ask_int("Number of scenes", default=cfg.scene_target)
        if cfg.has_leading:
            cfg.sync_target = p.choose("Beat-sync style", SYNC_TARGETS, default=cfg.sync_target)
            cfg.mode = p.choose("Cut rhythm", MODES, default=cfg.mode)
            if self._analyze:  # understand the audio BEFORE asking topic/vibe
                with contextlib.suppress(Exception):
                    p.say(self._analyze(cfg.leading))
        cfg.topic = p.ask("Video topic", default=cfg.idea)
        cfg.description = p.ask("Short description")
        cfg.vibe = p.ask("Vibe / mood")
        cfg.llm_vendor = p.choose("LLM vendor", VENDORS, default=cfg.llm_vendor)
        cfg.llm_auth = p.choose("LLM auth (cli=login, api=key)", AUTHS, default=cfg.llm_auth)
        return cfg
