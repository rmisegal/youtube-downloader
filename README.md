# youtube-downloader

A Windows PowerShell command-line tool that, given a single YouTube URL, downloads the
**video as mp4**, and/or extracts the **audio as mp3**, and/or downloads the **subtitles as `.srt`**
— in any combination — using [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) with FFmpeg supplied by
[`imageio-ffmpeg`](https://pypi.org/project/imageio-ffmpeg/).

The authoritative specification lives in [`docs/PRD.md`](docs/PRD.md) and
[`docs/PLAN.md`](docs/PLAN.md).

---

## Requirements

- **Python ≥ 3.10**
- **[uv](https://docs.astral.sh/uv/)** (the only supported package manager — never `pip`)
- **No system FFmpeg install** — the FFmpeg binary is bundled via `imageio-ffmpeg` and located
  automatically at runtime.
- **No GPU / CUDA** — download is I/O-bound, mp3 extraction uses FFmpeg on CPU, and subtitles are
  plain text. GPU is only relevant to a future, out-of-scope transcription feature (see below).

---

## Install

```powershell
uv sync
```

This resolves and installs all runtime and dev dependencies from the committed `uv.lock`. Do **not**
use `pip` or `requirements.txt`.

---

## Usage

Invoke from Windows PowerShell. The general form is:

```powershell
uv run python -m ytdl "<URL>" [--video] [--audio] [--subs] [-o DIR] [-n NAME] [--resolution H] [--sub-lang L]
```

### Examples

Download the video as mp4 (default when no mode flag is given):

```powershell
uv run python -m ytdl "<URL>"
```

Extract audio as mp3:

```powershell
uv run python -m ytdl "<URL>" --audio
```

Download English subtitles as `.srt`:

```powershell
uv run python -m ytdl "<URL>" --subs --sub-lang en
```

Combine all three modes into a chosen folder and base name, capped at 720p:

```powershell
uv run python -m ytdl "<URL>" --video --audio --subs -o .\downloads -n myfile --resolution 720
# Produces: .\downloads\myfile.mp4, .\downloads\myfile.mp3, .\downloads\myfile.en.srt
```

Print the code + config version and exit:

```powershell
uv run python -m ytdl --version
```

Show the run-command cheat-sheet (all commands with examples) and exit:

```powershell
uv run python -m ytdl --command
```

`--video`, `--audio`, and `--subs` are **independent toggles**; any combination is valid in a single
run, and the video is fetched only once. If **none** of them is supplied, the tool defaults to
`--video`.

---

## Flags

Taken verbatim from the argparse definition in
[`src/ytdl/cli/args.py`](src/ytdl/cli/args.py):

| Flag | Meaning | Default |
|------|---------|---------|
| `url` (positional) | The YouTube video URL. | required (usage error if omitted) |
| `--video` | Download best-quality mp4 (merged video+audio). | off — but auto-enabled if no mode flag is given |
| `--audio` | Extract mp3 audio. | off |
| `--subs` | Download subtitles as `.srt`. | off |
| `-o`, `--output-dir` | Output folder (created if missing). | from config (`./downloads`) |
| `-n`, `--name` | Output base file name (no extension). | video title (`%(title)s`) |
| `--resolution` | Max video height, e.g. `1080` or `720` (int). | best available |
| `--sub-lang` | Subtitle language code. | `en` |
| `--version` | Print code + config version and exit. | — |
| `-command`, `--command` | Show the run-command cheat-sheet (commands + examples) and exit. | — |

---

## Output naming

Files are written into the output directory using the chosen base name plus a mode-specific
extension:

| Mode | Output file |
|------|-------------|
| Video | `<name>.mp4` |
| Audio | `<name>.mp3` |
| Subtitles | `<name>.<lang>.srt` |

When `-n`/`--name` is omitted, the base name defaults to the video title (`%(title)s`). The output
directory is created automatically if it does not exist (idempotent — no error if it already does).

---

## Configuration overview

All tunables are **config-driven** — there are no hardcoded values in the code. Each tunable is read
via `ConfigManager.get("a.b", default)`; `src/ytdl/constants.py` holds only true constants. Both
config files carry `"version": "1.00"`, validated at startup against the supported versions; a
mismatch raises `ConfigVersionError` (exit code 5).

### `config/setup.json` (version 1.00)

| Key | Purpose |
|-----|---------|
| `version` | Config schema version (must be `1.00`). |
| `paths.output_dir` | Default output folder (`./downloads`). Overridden by `-o`. |
| `defaults.resolution` | Default max video height (`null` = best available). Overridden by `--resolution`. |
| `defaults.sub_lang` | Default subtitle language (`en`). Overridden by `--sub-lang`. |
| `defaults.modes` | Default modes when none requested (`["video"]`). |
| `audio.codec` | Audio codec for extraction (`mp3`). |
| `audio.quality` | Audio bitrate quality (`192`). |
| `subtitles.format` | Subtitle output format (`srt`). |
| `subtitles.include_auto` | Include auto-generated subtitles in addition to manual ones (`true`). |
| `ffmpeg.location` | FFmpeg locator strategy (`auto` = resolve via `imageio-ffmpeg`). |

### `config/rate_limits.json` (version 1.00)

The same **versioned rate-limit / queue structure** prescribed by the
`/glb-quality-code-guidlines` is applied here, with **YouTube** as the throttled external service.

| Key | Purpose |
|-----|---------|
| `version` | Config schema version (must be `1.00`). |
| `rate_limits.services.youtube.requests_per_minute` | Max YouTube requests per minute (`20`). |
| `rate_limits.services.youtube.concurrent_max` | Max concurrent YouTube requests (`2`). |
| `rate_limits.services.youtube.burst_size` | Allowed burst size (`5`). |
| `rate_limits.services.youtube.burst_window_seconds` | Burst window in seconds (`10`). |
| `rate_limits.services.youtube.retry_after_seconds` | Backoff before retry (`30`). |
| `rate_limits.services.youtube.max_retries` | Max retries on transient failure (`3`). |
| `rate_limits.default.*` | Fallback limits for any unconfigured service. |
| `queue.max_depth` | Max queued downloads (`100`). |
| `queue.drain_interval_seconds` | Queue drain interval (`1`). |
| `queue.timeout_seconds` | Per-item queue timeout (`300`). |
| `queue.overflow_strategy` | Strategy when the queue is full (`reject_oldest`). |

> **Fathom note:** The Fathom rate-limit keys referenced by the guideline are **N/A** to this project
> — there is no Fathom integration. The same versioned rate-limit/queue structure is instead applied
> to YouTube as the throttled external service, satisfying the audit's intent.

---

## Secrets / optional environment

Public YouTube videos require **no API key and no secrets**. Optional, user-supplied values may be
placed in a `.env` file (which is **gitignored**). Copy the template to get started:

```powershell
Copy-Item .env-example .env
```

| Variable | Purpose |
|----------|---------|
| `YTDL_PROXY` | Optional HTTP/HTTPS/SOCKS proxy URL passed to yt-dlp (e.g. `http://host:port`). |
| `YTDL_COOKIES_FILE` | Optional path to a Netscape-format `cookies.txt` for age/region-gated public videos. |

No secret literals appear anywhere in the source. `.gitignore` excludes `.env`, `cookies.txt`,
`*.key`, `*.pem`, and `downloads/`.

---

## Architecture

```
CLI (argparse)  ──►  YoutubeDownloaderSDK  ──►  services (Video / Audio / Subtitle / Metadata)
                                            └──►  infra (ytdlp_client, ffmpeg)
                                            └──►  shared (gatekeeper → rate_limit → queue, config, version)
```

- The **SDK (`YoutubeDownloaderSDK`) is the single entry point** for all business logic. The CLI
  (and any future GUI/REST surface) imports only the SDK — no business logic lives in `cli/`.
- **Services** subclass a shared `BaseDownloader` so the yt-dlp options builder, output template,
  and FFmpeg wiring are not duplicated.
- **Infra** confines `yt_dlp` to a single wrapper (`ytdlp_client.py`) and locates FFmpeg via
  `imageio-ffmpeg` (`ffmpeg.py`).
- **Shared** routes every YouTube network call through an `ApiGatekeeper` that enforces rate limits,
  retries transient failures with backoff, logs each call, and feeds a `DownloadQueue`.
- **Every source file is ≤ 150 code lines.**

---

## Testing

```powershell
uv run pytest tests/ --cov=src
uv run ruff check src/ tests/
```

Unit tests mock all external boundaries (`yt_dlp.YoutubeDL`, `imageio_ffmpeg.get_ffmpeg_exe`,
`subprocess`) — no network and no real FFmpeg are used. The suite enforces a coverage gate.

---

## Exit codes

Deterministic, matching the constants in [`src/ytdl/cli/main.py`](src/ytdl/cli/main.py):

| Code | Meaning |
|------|---------|
| `0` | Success. |
| `1` | Other / unexpected error. |
| `2` | Invalid or unavailable URL (also used for argparse/missing-url usage errors). |
| `3` | Network failure after retries. |
| `4` | Unsupported request. |
| `5` | Configuration version mismatch. |

---

## Future / out of scope (v1.00)

The following are **explicitly out of scope for v1.00** and listed here only for direction:

- **Batch / playlist CLI surface** — the engine and download queue already support multiple URLs;
  only a CLI mode is missing.
- **Subtitle translation** and multi-language subtitle download.
- **GPU-accelerated transcription** of downloaded audio. If added, it would integrate
  [`youtube-transcript-api`](https://pypi.org/project/youtube-transcript-api/) and, for local Whisper
  transcription, **reference** `C:\25D\GeneralLearning\transcribe-video\cuda_libs` **in place (never
  copied)** by prepending it to `PATH` before importing the CUDA-backed library — exactly the pattern
  used by transcribe-video's `transcribe.py`. This is the only place GPU/CUDA would ever enter the
  project.

  ```python
  # Future-only pattern (NOT used in v1.00):
  import os
  from pathlib import Path
  CUDA_LIBS = Path(r"C:\25D\GeneralLearning\transcribe-video\cuda_libs")
  os.environ["PATH"] = str(CUDA_LIBS) + os.pathsep + os.environ.get("PATH", "")
  ```

> **Removable-drive safety note (for future maintainers):** any future re-consultation of the
> knowledge graph that lives on the **D: USB drive** must first verify `Test-Path D:\` and stop if
> the drive is absent — blind access to a missing removable drive hangs. This is not part of v1.00.

## Known limitations (v1.00)

- When **both** `--video` and `--audio` are requested in the same run, yt-dlp's
  `keepvideo` (required so audio extraction does not delete the merged mp4) also
  leaves the intermediate per-stream files (e.g. `name.f137.mp4`, `name.f251.webm`)
  next to the final `name.mp4` / `name.mp3`. The required outputs are correct; the
  intermediates are harmless leftovers. Automatic cleanup is planned for a future release.
