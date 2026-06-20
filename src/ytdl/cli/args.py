"""argparse builder for the ytdl CLI.

Kept separate from :mod:`ytdl.cli.main` so the entry module stays small and
focused on delegation. This module only *describes* the CLI surface (PRD §3.1);
it contains no business logic.
"""

from __future__ import annotations

import argparse


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
    _add_mixer_args(parser)
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


def _add_mixer_args(parser: argparse.ArgumentParser) -> None:
    """Add the VJ video-mixer flags (PRD-mixer §3)."""
    parser.add_argument(
        "--mix",
        action="store_true",
        help="Switch to live video mixer / VJ playback mode (instead of downloading).",
    )
    parser.add_argument(
        "--dir",
        default=None,
        help="Folder of local video assets to mix (required with --mix).",
    )
    parser.add_argument(
        "--mode",
        choices=("option1", "option2"),
        default=None,
        help="Engine: option1 (FFmpeg->VLC, true crossfade) or option2 (dual-libVLC). Default: option2.",
    )
    parser.add_argument(
        "--selection",
        choices=("random", "manual"),
        default=None,
        help="Track selection: random (infinite shuffle) or manual (numbered picker). Default: random.",
    )
    parser.add_argument(
        "--crossfade-time",
        dest="crossfade_time",
        type=int,
        default=None,
        help="Crossfade overlap window in seconds. Default: 3.",
    )
    parser.add_argument(
        "--source-mix-time",
        dest="source_mix_time",
        type=float,
        default=None,
        help="Seconds into the source clip where the crossfade begins. Default: clip end.",
    )
    parser.add_argument(
        "--target-start-time",
        dest="target_start_time",
        type=float,
        default=None,
        help="In-point (seconds) where the target clip starts. Default: 0.",
    )
