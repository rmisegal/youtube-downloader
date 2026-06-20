"""CLI mixer/sampler/playlist run-handlers — delegate to the SDK (Rule 1).

Extracted from :mod:`ytdl.cli.main` so the entry module stays ≤150 lines (Rule 8).
NO business logic lives here: each handler builds the SDK, calls one method, and
maps domain exceptions to the deterministic exit codes in :mod:`ytdl.cli.exits`
(PRD-mixer §, PRD-playlist §9). The download path stays in ``main`` (its tests
patch this module's ``YoutubeDownloaderSDK``).
"""

from __future__ import annotations

import logging
import sys

from ytdl.cli.exits import (
    EXIT_GENERIC_ERROR,
    EXIT_PLAYBACK_DEP,
    EXIT_PLAYLIST,
    EXIT_RATE_LIMIT,
    EXIT_SUCCESS,
    EXIT_USAGE,
)
from ytdl.sdk.sdk import YoutubeDownloaderSDK
from ytdl.shared.errors import (
    PlaybackDependencyError,
    PlaylistError,
    RateLimitExceededError,
)

_LOGGER = logging.getLogger("ytdl.cli")


def _fail(label: str, exc: Exception, code: int) -> int:
    """Log + print a clear error to stderr and return the mapped exit code."""
    _LOGGER.error("%s: %s", label, exc)
    print(f"Error: {label}: {exc}", file=sys.stderr)
    return code


def run_mix(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Run the VJ video mixer over --dir; map exceptions to exit codes."""
    if not args.dir:
        print("Error: --dir is required with --mix.", file=sys.stderr)
        return EXIT_USAGE
    _LOGGER.info("phase=mix dir=%s mode=%s selection=%s", args.dir, args.mode, args.selection)
    sdk = YoutubeDownloaderSDK()
    try:
        result = sdk.mix_local_directory(
            args.dir,
            mode=args.mode,
            selection=args.selection,
            crossfade=args.crossfade_time,
            source_mix_time=args.source_mix_time,
            target_start_time=args.target_start_time,
        )
    except PlaybackDependencyError as exc:
        return _fail("Missing playback dependency — install VLC", exc, EXIT_PLAYBACK_DEP)
    except FileNotFoundError as exc:
        return _fail("Mix directory not found or drive not mounted", exc, EXIT_USAGE)
    except RateLimitExceededError as exc:
        return _fail("Rate limit / quota reached (protecting your account)", exc, EXIT_RATE_LIMIT)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("Unexpected error", exc, EXIT_GENERIC_ERROR)
    _LOGGER.info("phase=done mix mode=%s tracks=%s", result.get("mode"), result.get("track_count"))
    return EXIT_SUCCESS


def run_sample(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Run the folder sampler over --dir; map exceptions to exit codes."""
    if not args.dir:
        print("Error: --dir is required with --sample-play.", file=sys.stderr)
        return EXIT_USAGE
    _LOGGER.info("phase=sample dir=%s mode=%s play_for_sec=%s", args.dir, args.mode, args.play_for_sec)
    sdk = YoutubeDownloaderSDK()
    try:
        result = sdk.sample_play(args.dir, play_for_sec=args.play_for_sec, mode=args.mode)
    except PlaybackDependencyError as exc:
        return _fail("Missing playback dependency — install VLC", exc, EXIT_PLAYBACK_DEP)
    except FileNotFoundError as exc:
        return _fail("Sample directory not found or drive not mounted", exc, EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("Unexpected error", exc, EXIT_GENERIC_ERROR)
    _LOGGER.info("phase=done sample mode=%s tracks=%s", result.get("mode"), result.get("track_count"))
    return EXIT_SUCCESS


def run_playlist(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Run a declarative YAML playlist; map exceptions to exit codes."""
    _LOGGER.info("phase=playlist file=%s", args.playlist_file)
    sdk = YoutubeDownloaderSDK()
    try:
        result = sdk.play_playlist(args.playlist_file)
    except PlaylistError as exc:
        return _fail("Invalid or malformed playlist YAML", exc, EXIT_PLAYLIST)
    except PlaybackDependencyError as exc:
        return _fail("Missing playback dependency — install VLC", exc, EXIT_PLAYBACK_DEP)
    except FileNotFoundError as exc:
        return _fail("Playlist file or member not found", exc, EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("Unexpected error", exc, EXIT_GENERIC_ERROR)
    _LOGGER.info("phase=done playlist output=%s", result.get("output"))
    return EXIT_SUCCESS
