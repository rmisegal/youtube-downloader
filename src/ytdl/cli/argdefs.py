"""argparse flag-group helpers (mixer / playlist / analysis).

Kept out of :mod:`ytdl.cli.args` so each file stays ≤150 lines. Pure CLI-surface
description — no business logic.
"""

from __future__ import annotations

import argparse


def add_playlist_args(parser: argparse.ArgumentParser) -> None:
    """Add the sampler / per-clip duration / YAML playlist flags (PRD-playlist §3.1)."""
    parser.add_argument(
        "--sample-play", dest="sample_play", action="store_true",
        help="Preview --dir: crossfade random mid-band samples of each clip (uses --mode).",
    )
    parser.add_argument(
        "--play-for-sec", dest="play_for_sec", type=float, default=None,
        help="Seconds to play each clip before the crossfade (sampler or mix).",
    )
    parser.add_argument(
        "--playlist-file", dest="playlist_file", default=None,
        help="Path to a declarative YAML playlist to display/save/stream.",
    )


def add_movie_args(parser: argparse.ArgumentParser) -> None:
    """Add the movie-agent tools: YouTube search + segments-JSON → movie (PRD-movie-agent)."""
    parser.add_argument(
        "--search", dest="search", default=None,
        help="Search YouTube and print candidate videos (title/url/duration) as JSON, then exit.",
    )
    parser.add_argument(
        "--results", dest="search_results", type=int, default=8,
        help="Number of --search results to return. Default: 8.",
    )
    parser.add_argument(
        "--fetch-movie", dest="fetch_movie", default=None,
        help="Download every video in a segments JSON to seg_<n>.mp4 in --dir (shows progress).",
    )
    parser.add_argument(
        "--to-segments", dest="to_segments", default=None,
        help="Scaffold an editable segments JSON from a --search candidates file (write with -o).",
    )
    parser.add_argument(
        "--build-movie", dest="build_movie", default=None,
        help="Build a playlist from a Video Content Matcher segments JSON (videos in --dir).",
    )
    parser.add_argument(
        "--leading", dest="leading_audio", default=None,
        help="Optional leading audio (music score) for --build-movie; else clips keep their audio.",
    )
    parser.add_argument(
        "--sync", dest="sync_target", nargs="?", const="video_art", default=None,
        help="Beat-sync the movie cuts to --leading (optional content target, default video_art).",
    )
    parser.add_argument(
        "--produce", dest="produce", action="store_true",
        help="After --build-movie, immediately produce the film (run the playlist).",
    )


def add_analysis_args(parser: argparse.ArgumentParser) -> None:
    """Add the beat-sync audio-analyzer flags (PRD-beatsync §4.1)."""
    parser.add_argument(
        "--analyze", dest="analyze", default=None,
        help="Analyze an audio file's beats/bars/phrases/sections and exit (writes JSON with -o).",
    )
    parser.add_argument(
        "--fps", dest="analyze_fps", type=float, default=None,
        help="Target FPS for frame indices when analyzing. Default from config (30).",
    )
    parser.add_argument(
        "--levels", dest="analyze_levels", default=None,
        help="Comma list of analysis tiers: beat,bar,phrase,section. Default: all.",
    )
    parser.add_argument(
        "--format", dest="analyze_format", choices=("json", "csv"), default="json",
        help="Analyze output format written to -o. Default: json.",
    )


def add_mixer_args(parser: argparse.ArgumentParser) -> None:
    """Add the VJ video-mixer flags (PRD-mixer §3)."""
    parser.add_argument(
        "--mix", action="store_true",
        help="Switch to live video mixer / VJ playback mode (instead of downloading).",
    )
    parser.add_argument(
        "--dir", default=None, help="Folder of local video assets to mix (required with --mix).",
    )
    parser.add_argument(
        "--mode", choices=("option1", "option2"), default=None,
        help="Engine: option1 (FFmpeg->VLC, true crossfade) or option2 (dual-libVLC). Default: option2.",
    )
    parser.add_argument(
        "--selection", choices=("random", "manual"), default=None,
        help="Track selection: random (infinite shuffle) or manual (numbered picker). Default: random.",
    )
    parser.add_argument(
        "--crossfade-time", dest="crossfade_time", type=int, default=None,
        help="Crossfade overlap window in seconds. Default: 3.",
    )
    parser.add_argument(
        "--source-mix-time", dest="source_mix_time", type=float, default=None,
        help="Seconds into the source clip where the crossfade begins. Default: clip end.",
    )
    parser.add_argument(
        "--target-start-time", dest="target_start_time", type=float, default=None,
        help="In-point (seconds) where the target clip starts. Default: 0.",
    )
