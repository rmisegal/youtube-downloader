"""CLI handlers for the movie-pipeline (wizard → make-movie) and the segments scaffold.

Kept out of :mod:`ytdl.cli.movie_run` so each file stays ≤150 lines (Rule 8). Each
handler delegates to the SDK (Rule 1). For now: ``--to-segments`` scaffolds an editable
segments JSON from ``--search`` candidates; the full ``--make-movie`` pipeline + wizard
handlers land in later phases.
"""

from __future__ import annotations

import logging

from ytdl.cli.exits import EXIT_GENERIC_ERROR, EXIT_SUCCESS, EXIT_USAGE
from ytdl.cli.movie_run import run_build_movie, run_fetch_movie, run_search
from ytdl.cli.run import _fail
from ytdl.sdk.sdk import YoutubeDownloaderSDK
from ytdl.services.pipeline.config import MovieConfig

_LOGGER = logging.getLogger("ytdl.cli")


def dispatch_movie(args) -> int | None:  # noqa: ANN001 - argparse.Namespace
    """Route a movie-agent / pipeline flag to its handler; ``None`` if none matched."""
    handlers = [
        ("search", run_search), ("fetch_movie", run_fetch_movie),
        ("to_segments", run_to_segments), ("movie_wizard", run_movie_wizard),
        ("plan_movie", run_plan_movie), ("make_movie", run_make_movie),
        ("build_movie", run_build_movie),
    ]
    for attr, handler in handlers:
        if getattr(args, attr, None):
            return handler(args)
    return None


def _apply_overrides(cfg: MovieConfig, args) -> MovieConfig:  # noqa: ANN001 - argparse.Namespace
    """Apply optional CLI overrides (scenes/vendor/auth/leading) onto a loaded config."""
    if args.scenes:
        cfg.scene_target = args.scenes
    if args.vendor:
        cfg.llm_vendor = args.vendor
    if args.auth:
        cfg.llm_auth = args.auth
    if getattr(args, "leading_audio", None):
        cfg.leading = args.leading_audio
    return cfg


def run_movie_wizard(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Run the interactive setup wizard and save a config.json."""
    out = args.config or args.output_dir or "config.json"
    _LOGGER.info("phase=movie-wizard out=%s", out)
    try:
        path = YoutubeDownloaderSDK().movie_wizard(out)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("Wizard failed", exc, EXIT_GENERIC_ERROR)
    print(f"Saved config -> {path}")
    print(f'Run it: --make-movie --config "{path}"')
    return EXIT_SUCCESS


def run_plan_movie(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Run only STRUCTURE so the agent can author script.json before --make-movie."""
    if not args.config:
        return _fail("--plan-movie needs --config <config.json>", ValueError("run --movie-wizard first"),
                     EXIT_USAGE)
    try:
        cfg = _apply_overrides(MovieConfig.load(args.config), args)
        result = YoutubeDownloaderSDK().plan_movie(cfg)
    except (OSError, ValueError) as exc:
        return _fail("Could not plan the movie", exc, EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("Movie planning failed", exc, EXIT_GENERIC_ERROR)
    print(f"Planned {len(result['scenes'])} scenes -> {result['structure_path']}")
    print(f"Author the script at {result['script_path']} (movie-script-writer), then --make-movie")
    return EXIT_SUCCESS


def run_make_movie(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Run the full idea+song → mixed-video pipeline from a config.json."""
    if not args.config:
        return _fail("--make-movie needs --config <config.json>", ValueError("run --movie-wizard first"),
                     EXIT_USAGE)
    _LOGGER.info("phase=make-movie config=%s", args.config)
    try:
        cfg = _apply_overrides(MovieConfig.load(args.config), args)
        result = YoutubeDownloaderSDK().make_movie(cfg)
    except (OSError, ValueError) as exc:
        return _fail("Could not run the movie pipeline", exc, EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("Movie pipeline failed", exc, EXIT_GENERIC_ERROR)
    print(f"Movie pipeline complete -> {result['build_dir']}")
    print(f"  scenes={result['scenes']} matched={result['matched']} "
          f"downloaded={result['downloaded']} failed={result['failed']}")
    print(f"  playlist: {result['playlist']}\n  report: {result['report']}")
    return EXIT_SUCCESS


def run_to_segments(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Scaffold an editable segments JSON from a ``--search`` candidates file."""
    out = args.output_dir or "segments.json"
    _LOGGER.info("phase=to-segments candidates=%s out=%s", args.to_segments, out)
    try:
        path = YoutubeDownloaderSDK().to_segments(args.to_segments, out)
    except (OSError, ValueError) as exc:
        return _fail("Could not read the candidates JSON", exc, EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("Unexpected error", exc, EXIT_GENERIC_ERROR)
    print(f"Scaffolded segments -> {path}")
    print("Edit start_time/duration per scene, then: --fetch-movie then --build-movie")
    return EXIT_SUCCESS
