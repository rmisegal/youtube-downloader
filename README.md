# youtube-downloader

Windows PowerShell CLI to download a YouTube video as **mp4**, extract audio as **mp3**,
and/or download subtitles as **`.srt`** — in any combination — using `yt-dlp` with FFmpeg
supplied by `imageio-ffmpeg` (no system FFmpeg, no GPU required).

> Foundation in place (config, constants, versioning). Full CLI/SDK arrives in later phases.
> See `docs/PRD.md`, `docs/PLAN.md`, and `docs/TODO.md` for the authoritative specification.

## Install

```powershell
uv sync
```

## Usage (target interface)

```powershell
uv run python -m ytdl "<URL>" [--video] [--audio] [--subs] -o .\downloads -n sample --resolution 720 --sub-lang en
```

## Toolchain

- Package manager: **uv** only (`uv sync`, `uv add`, `uv run`). No `pip`, no `requirements.txt`.
- Tests/lint: `uv run pytest`, `uv run ruff check src/ tests/`.
