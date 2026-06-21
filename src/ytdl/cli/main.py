"""CLI entry point — parses args and delegates 100% to the SDK (Rule 1).

NO business logic lives here: argparse describes the surface (see
:mod:`ytdl.cli.args`), this module reconfigures I/O, sets up logging, routes to
the run-handlers (mix/sample/playlist live in :mod:`ytdl.cli.run`; the download
path stays here), and maps domain exceptions to deterministic exit codes
(:mod:`ytdl.cli.exits`, PRD §3.3).
"""

from __future__ import annotations

import contextlib
import logging
import sys

from ytdl.cli.args import build_parser
from ytdl.cli.exits import (
    EXIT_CONFIG_VERSION,
    EXIT_GENERIC_ERROR,
    EXIT_INVALID_URL,
    EXIT_NETWORK_ERROR,
    EXIT_PLAYBACK_DEP,
    EXIT_PLAYLIST,
    EXIT_RATE_LIMIT,
    EXIT_SUCCESS,
    EXIT_UNSUPPORTED,
    EXIT_USAGE,
)
from ytdl.cli.movie_run import run_build_movie, run_fetch_movie, run_search
from ytdl.cli.pipeline_run import run_to_segments
from ytdl.cli.playlist import is_playlist_url, resolve_playlist_choice
from ytdl.cli.run import _fail, run_analyze, run_mix, run_playlist, run_sample
from ytdl.cli.usage import commands_text
from ytdl.sdk.sdk import YoutubeDownloaderSDK
from ytdl.shared import logsetup
from ytdl.shared.config import ConfigManager
from ytdl.shared.errors import (
    ConfigVersionError,
    InvalidUrlError,
    NetworkError,
    RateLimitExceededError,
    UnsupportedRequestError,
)

_LOGGER = logging.getLogger("ytdl.cli")

# Re-export the exit codes so existing callers/tests can use ``cli.EXIT_*``.
__all__ = [
    "EXIT_CONFIG_VERSION",
    "EXIT_GENERIC_ERROR",
    "EXIT_INVALID_URL",
    "EXIT_NETWORK_ERROR",
    "EXIT_PLAYBACK_DEP",
    "EXIT_PLAYLIST",
    "EXIT_RATE_LIMIT",
    "EXIT_SUCCESS",
    "EXIT_UNSUPPORTED",
    "EXIT_USAGE",
    "main",
]


def _configure_io() -> None:
    """Reconfigure stdout/stderr to UTF-8 (Hebrew/Unicode-safe) when possible."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            with contextlib.suppress(ValueError, OSError):
                reconfigure(encoding="utf-8")


def _configure_logging(verbose: bool) -> None:
    """Set up clean logging: rotating file (DEBUG) + console (ERROR / INFO if -v)."""
    logsetup.configure_logging(
        ConfigManager(file_name="setup.json"), verbose=verbose
    )


def _print_commands() -> int:
    """Print the run-command cheat-sheet and return success (``--command``)."""
    print(commands_text())
    return EXIT_SUCCESS


def _print_version() -> int:
    """Print code + config version and return success (PRD §3.1 ``--version``)."""
    code_version = YoutubeDownloaderSDK.version()
    config_version = ConfigManager(file_name="setup.json").version
    print(f"ytdl code version: {code_version}")
    print(f"config version: {config_version}")
    return EXIT_SUCCESS


def _resolve_playlist(sdk: YoutubeDownloaderSDK, args) -> dict:  # noqa: ANN001
    """Decide playlist handling from flags, or prompt the user when applicable."""
    if args.no_playlist:
        return {"no_playlist": True, "playlist_items": None}
    if args.playlist_items:
        return {"no_playlist": False, "playlist_items": args.playlist_items}
    if is_playlist_url(args.url):
        return resolve_playlist_choice(sdk, args.url)
    return {"no_playlist": False, "playlist_items": None}


def _run_download(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Delegate the download to the SDK and map exceptions to exit codes."""
    _LOGGER.info("phase=resolve url=%s", args.url)
    sdk = YoutubeDownloaderSDK()
    try:
        choice = _resolve_playlist(sdk, args)
        result = sdk.download(
            args.url,
            video=args.video,
            audio=args.audio,
            subs=args.subs,
            output_dir=args.output_dir,
            name=args.name,
            resolution=args.resolution,
            sub_lang=args.sub_lang,
            no_playlist=choice["no_playlist"],
            playlist_items=choice["playlist_items"],
        )
    except InvalidUrlError as exc:
        return _fail("Invalid or unavailable URL", exc, EXIT_INVALID_URL)
    except RateLimitExceededError as exc:
        return _fail("Rate limit / quota reached (protecting your account)", exc, EXIT_RATE_LIMIT)
    except NetworkError as exc:
        return _fail("Network failure after retries", exc, EXIT_NETWORK_ERROR)
    except UnsupportedRequestError as exc:
        return _fail("Unsupported request", exc, EXIT_UNSUPPORTED)
    except ConfigVersionError as exc:
        return _fail("Configuration version mismatch", exc, EXIT_CONFIG_VERSION)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("Unexpected error", exc, EXIT_GENERIC_ERROR)
    _LOGGER.info("phase=done modes=%s output=%s", result.get("modes"), result.get("output_dir"))
    return EXIT_SUCCESS


def main(argv: list[str] | None = None) -> int:
    """Parse args and delegate to the SDK; return a deterministic exit code."""
    _configure_io()
    args = build_parser().parse_args(argv)
    _configure_logging(args.verbose)
    if args.command:
        return _print_commands()
    if args.version:
        return _print_version()
    if args.analyze:
        return run_analyze(args)
    if args.search:
        return run_search(args)
    if args.fetch_movie:
        return run_fetch_movie(args)
    if args.to_segments:
        return run_to_segments(args)
    if args.build_movie:
        return run_build_movie(args)
    if args.mix:
        return run_mix(args)
    if args.sample_play:
        return run_sample(args)
    if args.playlist_file:
        return run_playlist(args)
    if not args.url:
        print("Error: the 'url' argument is required.", file=sys.stderr)
        return EXIT_USAGE
    return _run_download(args)
