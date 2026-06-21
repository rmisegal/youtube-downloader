"""argparse builder for the ytdl CLI.

Kept separate from :mod:`ytdl.cli.main` so the entry module stays small and
focused on delegation. This module only *describes* the CLI surface (PRD §3.1);
it contains no business logic.
"""

from __future__ import annotations

import argparse

from ytdl.cli.argdefs import (
    add_analysis_args,
    add_mixer_args,
    add_movie_args,
    add_playlist_args,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for ``python -m ytdl`` (PRD §3.1)."""
    parser = argparse.ArgumentParser(
        prog="ytdl",
        description=(
            "Download a YouTube video as mp4, and/or extract mp3 audio, "
            "and/or download subtitles as .srt — in any combination."
        ),
    )
    parser.add_argument("url", nargs="?", help="The YouTube video URL.")
    parser.add_argument(
        "--video", action="store_true", help="Download best-quality mp4."
    )
    parser.add_argument(
        "--audio", action="store_true", help="Extract mp3 audio."
    )
    parser.add_argument(
        "--subs", action="store_true", help="Download subtitles as .srt."
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        default=None,
        help="Output folder (created if missing). Default from config.",
    )
    parser.add_argument(
        "-n",
        "--name",
        default=None,
        help="Output base file name (no extension). Default: video title.",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=None,
        help="Max video height, e.g. 1080 or 720. Default: best available.",
    )
    parser.add_argument(
        "--sub-lang",
        dest="sub_lang",
        default=None,
        help="Subtitle language code. Default: en.",
    )
    parser.add_argument(
        "--no-playlist",
        dest="no_playlist",
        action="store_true",
        help="If the URL is part of a playlist, download only the single video.",
    )
    parser.add_argument(
        "--playlist-items",
        dest="playlist_items",
        default=None,
        help="Download only these playlist items, e.g. '1,3,5' or '1-5' (skips the prompt).",
    )
    add_mixer_args(parser)
    add_playlist_args(parser)
    add_analysis_args(parser)
    add_movie_args(parser)
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="Show INFO-level progress on the console (default: errors only).",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print code + config version and exit.",
    )
    parser.add_argument(
        "-command",
        "--command",
        action="store_true",
        help="Show the run-command cheat-sheet (with examples) and exit.",
    )
    return parser

