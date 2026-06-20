"""Run-command cheat-sheet for the ``--command`` flag.

Kept out of :mod:`ytdl.cli.main` so the entry module stays small (Rule 8).
Pure presentation text — no business logic, no imports of app internals.
"""

from __future__ import annotations

COMMANDS_HELP: str = """\
ytdl — run commands & examples
==============================

Download the video as mp4 (default when no mode flag is given):
  uv run python -m ytdl "<URL>"

Extract audio only as mp3:
  uv run python -m ytdl "<URL>" --audio

Download subtitles only as .srt (default language: en):
  uv run python -m ytdl "<URL>" --subs --sub-lang en

Everything at once, into a chosen folder/name, capped at 720p:
  uv run python -m ytdl "<URL>" --video --audio --subs -o .\\downloads -n myfile --resolution 720

Cap the video resolution (best quality if omitted):
  uv run python -m ytdl "<URL>" --resolution 1080

Playlist/mix URL — you are shown the number of AVAILABLE items and asked to
download all, select specific ones, or only this video:
  uv run python -m ytdl "<PLAYLIST_URL>"

Download only this video from a list URL (no prompt):
  uv run python -m ytdl "<URL&list=...>" --no-playlist

Download only specific playlist items (no prompt):
  uv run python -m ytdl "<PLAYLIST_URL>" --playlist-items 1,3,5

Print code + config version:
  uv run python -m ytdl --version

Show this command list:
  uv run python -m ytdl --command

VIDEO MIXER / VJ MODE (requires VLC installed):

Mix a folder of videos with crossfades (dual-libVLC gapless, random order):
  uv run python -m ytdl --mix --dir "C:\\videos"

True FFmpeg crossfade engine, manual track picker, 2s crossfade:
  uv run python -m ytdl --mix --dir "C:\\videos" --mode option1 --selection manual --crossfade-time 2

Set the crossfade mix points (mix out of the source at 30s; start the target at 10s):
  uv run python -m ytdl --mix --dir "C:\\videos" --source-mix-time 30 --target-start-time 10

SAMPLER / PLAYLIST MODE (requires VLC installed):

Preview a folder — crossfade a random mid-band sample of each clip, looping:
  uv run python -m ytdl --sample-play --dir "C:\\videos"

Sampler with a fixed per-clip play time and the FFmpeg engine:
  uv run python -m ytdl --sample-play --dir "C:\\videos" --play-for-sec 5 --mode option1

Play / save / stream a declarative YAML playlist:
  uv run python -m ytdl --playlist-file "C:\\lists\\show.yaml"

Flags:
  url               The YouTube video URL (positional).
  --video           Download best-quality mp4.
  --audio           Extract mp3 audio.
  --subs            Download subtitles as .srt (manual + auto-generated).
  -o, --output-dir  Output folder (created if missing). Default: ./downloads.
  -n, --name        Output base file name (no extension). Default: video title.
  --resolution      Max video height, e.g. 1080 or 720. Default: best available.
  --sub-lang        Subtitle language code. Default: en.
  --no-playlist     For a list URL, download only the single video.
  --playlist-items  Download only these items, e.g. 1,3,5 or 1-5 (skips prompt).
  --sample-play     Preview --dir: crossfade random mid-band samples (uses --mode).
  --play-for-sec    Seconds to play each clip before the crossfade (sampler/mix).
  --playlist-file   Path to a YAML playlist to display/save/stream.
  --version         Print code + config version and exit.
  --command         Show this run-command cheat-sheet and exit.

Mixer flags (with --mix):
  --dir             Folder of local videos to mix (required).
  --mode            option1 (FFmpeg->VLC, true crossfade) | option2 (dual-libVLC). Default option2.
  --selection       random (infinite shuffle) | manual (numbered picker). Default random.
  --crossfade-time  Crossfade overlap seconds. Default 3.
  --source-mix-time Seconds into the source where the crossfade begins. Default: clip end.
  --target-start-time  In-point seconds where the target starts. Default 0.
"""


def commands_text() -> str:
    """Return the run-command cheat-sheet text."""
    return COMMANDS_HELP
