"""CLI handlers for the movie-agent tools (``--search`` / ``--build-movie``).

Kept out of :mod:`ytdl.cli.run` so each file stays ≤150 lines (Rule 8). Each handler
delegates to the SDK (Rule 1): ``--search`` lists candidate YouTube videos for the
Video Content Matcher; ``--build-movie`` turns the matcher's segments JSON into a
playlist (and, with ``--produce``, renders the film via the playlist runner).
"""

from __future__ import annotations

import json
import logging

from ytdl.cli.exits import EXIT_GENERIC_ERROR, EXIT_RATE_LIMIT, EXIT_SUCCESS, EXIT_USAGE
from ytdl.cli.run import _fail, run_playlist
from ytdl.sdk.sdk import YoutubeDownloaderSDK
from ytdl.shared.errors import RateLimitExceededError

_LOGGER = logging.getLogger("ytdl.cli")


def run_search(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Search YouTube and print candidate videos as JSON (movie-agent tool)."""
    _LOGGER.info("phase=search query=%s results=%s", args.search, args.search_results)
    try:
        results = YoutubeDownloaderSDK().search(args.search, results=args.search_results)
    except RateLimitExceededError as exc:
        return _fail("Rate limit / quota reached (protecting your account)", exc, EXIT_RATE_LIMIT)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("YouTube search failed", exc, EXIT_GENERIC_ERROR)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return EXIT_SUCCESS


def run_fetch_movie(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Download every segment's video to seg_<n>.mp4 with [N/total] progress."""
    _LOGGER.info("phase=fetch-movie json=%s dir=%s", args.fetch_movie, args.dir)
    try:
        result = YoutubeDownloaderSDK().fetch_movie(args.fetch_movie, args.dir or ".")
    except (OSError, ValueError) as exc:
        return _fail("Could not read the segments JSON", exc, EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("Unexpected error", exc, EXIT_GENERIC_ERROR)
    return EXIT_SUCCESS if not result["failed"] else EXIT_GENERIC_ERROR


def run_build_movie(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Build a playlist from a matcher segments JSON; optionally produce the film."""
    _LOGGER.info("phase=build-movie json=%s dir=%s", args.build_movie, args.dir)
    try:
        out = YoutubeDownloaderSDK().build_movie(
            args.build_movie, args.dir or ".",
            leading_audio=args.leading_audio, out_path=args.output_dir,
        )
    except (OSError, ValueError) as exc:
        return _fail("Could not build the movie playlist", exc, EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("Unexpected error", exc, EXIT_GENERIC_ERROR)
    print(f"Built movie playlist: {out}")
    if not args.produce:
        print(f'Produce it with: --playlist-file "{out}"')
        return EXIT_SUCCESS
    args.playlist_file = out
    return run_playlist(args)
