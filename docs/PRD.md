# PRD — YouTube Downloader (Python CLI)

| Field | Value |
|-------|-------|
| Project | `youtube-downloader` |
| Location | `C:\25D\app\youtube-downloader` |
| Document version | 1.00 |
| Code version (target) | 1.00 |
| Config version (target) | 1.00 |
| Date | 2026-06-20 |
| Author | Generated for rmisegal@gmail.com |
| Status | Approved — ready for implementation |

---

## 1. Overview & Goals

### 1.1 Purpose
A command-line Python tool that, given a **YouTube URL**, downloads the **video as mp4**, and/or extracts the
**audio as mp3**, and/or downloads the **subtitles as `.srt`** — in any combination — into a chosen **output
folder** under a chosen **output file name**. It runs from **Windows PowerShell**.

### 1.2 One-sentence scope
> `uv run python -m ytdl <URL> [--video] [--audio] [--subs] [-o DIR] [-n NAME] [--resolution H] [--sub-lang L]`

### 1.3 Success criteria
1. A single URL can produce, in one invocation, any combination of `sample.mp4`, `sample.mp3`,
   `sample.<lang>.srt` in the requested folder with the requested base name.
2. Runs on Windows PowerShell with **no system FFmpeg install** and **no GPU** required.
3. Passes the full `/glb-quality-code-guidlines` audit (all 14 rules) — see §9.

### 1.4 Non-goals
- No GUI and no web service (the SDK is built so these *could* be added later without touching internals).
- No playlist/channel batch UX surface (the engine/queue can handle multiple URLs, but the CLI targets a
  single URL; batch is a future enhancement).
- No DRM circumvention, no age-gate/login bypass beyond user-supplied cookies, no scraping of private content.

---

## 2. Background & Reuse Decisions (do not reinvent the wheel)

These decisions come from researching existing local assets and Dr. Segal's knowledge graph before designing.

| Decision | Source of truth | Why |
|----------|-----------------|-----|
| **Engine = `yt-dlp`** | Dr. Segal's consolidated knowledge graph (`D:\graphify-shards\_consolidated\graphify-out\graph.json`). Nodes: *YouTube Skill → uses → yt-dlp*, *→ uses → youtube-transcript-api*. | The corpus already standardizes on `yt-dlp` for YouTube download/metadata. `yt-dlp` natively does mp4 download, mp3 extraction, and subtitle download via FFmpeg post-processors — no custom downloader needed. |
| **FFmpeg via `imageio-ffmpeg`** | `C:\25D\GeneralLearning\transcribe-video\core\splitter.py` (`imageio_ffmpeg.get_ffmpeg_exe()` + `subprocess`). | No system FFmpeg install required; the binary ships with the pip package. `yt-dlp` is pointed at it via `ffmpeg_location`. |
| **No GPU for core features** | Analysis: download is I/O; mp3 uses FFmpeg CPU `libmp3lame`; subtitles are text. | CUDA adds nothing to download/extract/subtitle work. GPU is documented for a *future* transcription feature only (§10). |
| **`youtube-transcript-api` for future transcripts** | Same graph node above. | Reserved for the out-of-scope transcription extension (§10), not used in v1.00. |

> **Removable-drive note:** the knowledge graph lives on the **D: USB drive**. Any future re-consultation must
> first verify `Test-Path D:\` and stop if absent. (Verified connected during research for this PRD.)

---

## 3. Functional Requirements

### 3.1 Inputs / CLI contract
Invoked from PowerShell: `uv run python -m ytdl <URL> [options]`

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `url` | positional, required | — | The YouTube video URL. |
| `--video` | flag | on if no output flag given | Download best-quality **mp4** (merged video+audio). |
| `--audio` | flag | off | Extract **mp3** audio. |
| `--subs` | flag | off | Download **subtitles** as `.srt`. |
| `-o`, `--output-dir` | path | from config (`./downloads`) | Output folder; **created if missing**. |
| `-n`, `--name` | string | `%(title)s` template | Output base file name (no extension). |
| `--resolution` | int | best available | Max video height (e.g. `1080`, `720`). Video only. |
| `--sub-lang` | string | `en` | Subtitle language code. Subs only. |
| `--version` | flag | — | Print code + config version and exit. |

**Combinability:** `--video`, `--audio`, `--subs` are **independent toggles**; any combination is valid in one
run. If **none** is supplied, the tool defaults to `--video`.

### 3.2 Outputs
| Mode | Result file | Mechanism |
|------|-------------|-----------|
| Video | `<name>.mp4` | `format="bv*[height<=RES]+ba/b"`, `merge_output_format="mp4"` |
| Audio | `<name>.mp3` | post-processor `FFmpegExtractAudio`, `preferredcodec="mp3"`, `preferredquality` from config |
| Subs | `<name>.<lang>.srt` | `writesubtitles` + `writeautomaticsub` (manual **and** auto-generated), `subtitleslangs=[lang]`, converted to `srt` |

### 3.3 Behavioral requirements
- **UTF-8 stdout** reconfiguration on startup (Hebrew/Unicode-safe), mirroring transcribe-video entry scripts.
- **Progress + structured logging** for each phase (resolve → download → post-process → write).
- **Deterministic exit codes:** `0` success; non-zero on invalid URL, network failure after retries,
  unsupported request, or config-version mismatch.
- **Idempotent output dir creation** (no error if folder already exists).
- **No interactive prompts** (PowerShell non-interactive safe).

---

## 4. Architecture (OOP, SDK-first, every file ≤ 150 code lines)

```
youtube-downloader/
├── pyproject.toml              # uv project; ruff/pytest/coverage config; version 1.00
├── uv.lock                     # committed lockfile
├── .env-example                # optional secret placeholders (committed)
├── .gitignore                  # ignores .env, cookies.txt, *.key, downloads/
├── README.md
├── config/
│   ├── setup.json              # app config (version 1.00)
│   └── rate_limits.json        # rate limits + queue config (version 1.00)
├── docs/
│   └── PRD.md                  # this document
├── src/
│   ├── main.py                 # `python -m ytdl` entry shim (omitted from coverage)
│   └── ytdl/
│       ├── __init__.py
│       ├── constants.py        # immutable constants + default fallbacks
│       ├── shared/
│       │   ├── version.py      # __version__ = "1.00"
│       │   ├── config.py       # ConfigManager: load JSON, .get("a.b", default), version validation
│       │   ├── rate_limit.py   # RateLimiter (sliding-window / token-bucket) from config
│       │   ├── gatekeeper.py   # ApiGatekeeper.execute(callable, ...): rate check + retry + logging
│       │   └── queue.py        # DownloadQueue: FIFO, max_depth, drain, overflow strategy
│       ├── infra/
│       │   ├── ffmpeg.py       # FfmpegLocator -> imageio_ffmpeg.get_ffmpeg_exe()
│       │   └── ytdlp_client.py # thin wrapper over yt_dlp.YoutubeDL; net calls go via ApiGatekeeper
│       ├── services/
│       │   ├── base.py         # BaseDownloader: shared ydl-opts/outtmpl/ffmpeg wiring (inheritance)
│       │   ├── video.py        # VideoDownloader (mp4 + resolution)
│       │   ├── audio.py        # AudioDownloader (mp3 post-processor)
│       │   ├── subtitles.py    # SubtitleDownloader (srt, manual+auto, lang)
│       │   └── metadata.py     # info/title extraction for filename templating
│       ├── sdk/
│       │   └── sdk.py          # YoutubeDownloaderSDK — SINGLE entry point
│       └── cli/
│           └── main.py         # argparse only; delegates 100% to the SDK
└── tests/
    ├── conftest.py             # shared fixtures (mock YoutubeDL, mock ffmpeg, sample config)
    └── unit/                   # mirrors src/ytdl/ structure
```

### 4.1 Layering (matches the SDK pattern of the guideline)
```
CLI (argparse)  ──►  YoutubeDownloaderSDK  ──►  services (Video/Audio/Subtitle/Metadata)
                                            └──►  infra (ytdlp_client, ffmpeg)
                                            └──►  shared (gatekeeper → rate_limit → queue, config, version)
```
- **Rule 1 — SDK gatekeeping:** the CLI (and any future GUI/REST) imports **only** `YoutubeDownloaderSDK`. No
  business logic lives in `cli/`. Every operation (resolve metadata, download video/audio/subs) is a public
  SDK method.
- **Rule 2 — No duplication:** `BaseDownloader` owns the shared `yt-dlp` options builder, `outtmpl`
  construction, and `ffmpeg_location` wiring. `VideoDownloader` / `AudioDownloader` / `SubtitleDownloader`
  subclass it and override only their format/post-processor specifics.
- **Rules 3–5 — Gatekeeper + rate control + queue:** all YouTube network calls (`extract_info`, `download`)
  are executed through `ApiGatekeeper.execute()`, which (a) enforces `RateLimiter` limits read from
  `rate_limits.json`, (b) retries transient failures with backoff, (c) logs every call, and (d) feeds a
  `DownloadQueue` (FIFO, configurable `max_depth`, drain interval, overflow strategy) so multi-URL/playlist
  overflow is **queued, never dropped or crashed**.

---

## 5. yt-dlp Option Mapping (implementation reference)

```python
# Video (mp4)
opts = {
    "format": f"bv*[height<={res}]+ba/b" if res else "bv*+ba/b",
    "merge_output_format": "mp4",
}

# Audio (mp3)
opts["postprocessors"] = [{
    "key": "FFmpegExtractAudio",
    "preferredcodec": cfg.get("audio.codec", "mp3"),
    "preferredquality": cfg.get("audio.quality", "192"),
}]

# Subtitles (srt, manual + auto)
opts.update({
    "writesubtitles": True,
    "writeautomaticsub": True,
    "subtitleslangs": [sub_lang],        # default "en"
    "subtitlesformat": "srt",
    "postprocessors": [{"key": "FFmpegSubtitlesConvertor", "format": "srt"}],
})

# Common
opts["ffmpeg_location"] = FfmpegLocator().exe_dir()      # imageio_ffmpeg.get_ffmpeg_exe() parent dir
opts["outtmpl"] = str(Path(output_dir) / f"{name}.%(ext)s")
```

> When multiple modes are combined, the SDK builds the union of post-processors (audio extraction + subtitle
> conversion) over a single resolved info dict so the video is fetched once.

---

## 6. Configuration & Secrets

### 6.1 `config/setup.json` (version 1.00)
```json
{
  "version": "1.00",
  "paths":     { "output_dir": "./downloads" },
  "defaults":  { "resolution": null, "sub_lang": "en", "modes": ["video"] },
  "audio":     { "codec": "mp3", "quality": "192" },
  "subtitles": { "format": "srt", "include_auto": true },
  "ffmpeg":    { "location": "auto" }
}
```

### 6.2 `config/rate_limits.json` (version 1.00)
```json
{
  "version": "1.00",
  "rate_limits": {
    "services": {
      "youtube": {
        "requests_per_minute": 20,
        "concurrent_max": 2,
        "burst_size": 5,
        "burst_window_seconds": 10,
        "retry_after_seconds": 30,
        "max_retries": 3
      }
    },
    "default": {
      "requests_per_minute": 30,
      "concurrent_max": 5,
      "retry_after_seconds": 30,
      "max_retries": 3
    }
  },
  "queue": {
    "max_depth": 100,
    "drain_interval_seconds": 1,
    "timeout_seconds": 300,
    "overflow_strategy": "reject_oldest"
  }
}
```
> **Fathom note (guideline §4):** Fathom Analytics is **N/A** to this project — there is no Fathom integration.
> The same *versioned rate-limit/queue structure* the guideline prescribes is applied to **YouTube** as the
> throttled external service. This is documented here to satisfy the audit's intent.

### 6.3 No hardcoded values (Rule 11)
- Code reads every tunable via `ConfigManager.get("a.b", default)`.
- `constants.py` holds only true constants (supported extensions, mode names, format templates).
- Function-parameter defaults act as last-resort fallbacks only.

### 6.4 Secrets (Rule 13)
- Public YouTube videos need **no API key**. Optional, user-supplied values go in `.env`:
```env
# .env-example (committed)
YTDL_PROXY=
YTDL_COOKIES_FILE=
```
- `.gitignore` includes: `.env`, `cookies.txt`, `*.key`, `*.pem`, `downloads/`.
- No secret literals anywhere in source.

### 6.5 Versioning (Rule 6)
- `src/ytdl/shared/version.py`: `__version__ = "1.00"`.
- Both JSON config files carry `"version": "1.00"`.
- Startup validates config version against `SUPPORTED_CONFIG_VERSIONS = ["1.00"]`; mismatch → `ConfigVersionError`.

---

## 7. Tooling & Dependencies (Rule 14 — uv mandatory)

| Concern | Choice |
|---------|--------|
| Package manager | **uv** only — `uv sync`, `uv add`, `uv run`. No `pip`, no `requirements.txt`. |
| Runtime deps | `yt-dlp`, `imageio-ffmpeg` |
| Dev deps | `pytest`, `pytest-cov`, `ruff` |
| Lockfile | committed `uv.lock` |
| Python | 3.10+ |

`pyproject.toml` includes `[tool.ruff]` (line-length 100; rules `E,F,W,I,N,UP,B,C4,SIM`; ignore `E501`),
`[tool.coverage.run]` (`source=["src"]`, omit `src/main.py`), and `[tool.coverage.report]` (`fail_under = 85`).

---

## 8. Testing Strategy (Rule 7 — TDD)

- Tests mirror `src/ytdl/` under `tests/unit/`; one test file per module; files also ≤150 lines.
- **Mock all external boundaries:** `yt_dlp.YoutubeDL`, `imageio_ffmpeg.get_ffmpeg_exe`, `subprocess`. **No
  network and no real FFmpeg** in unit tests.
- Cover **happy path + error cases** (invalid URL, empty/`None` args, rate-limit overflow → queued,
  config-version mismatch, missing output dir auto-created).
- Shared fixtures in `conftest.py` (`mock_ytdl`, `sample_config`, `tmp_output_dir`).
- Coverage gate **≥ 85%** enforced by the coverage config; the suite fails below it.

---

## 9. Compliance Matrix — `/glb-quality-code-guidlines` (all 14 rules)

| # | Rule | How this PRD satisfies it |
|---|------|---------------------------|
| 1 | SDK architecture | `YoutubeDownloaderSDK` is the single entry point; CLI delegates fully (§4.1). |
| 2 | OOP / no duplication | `BaseDownloader` + subclasses; shared option builder (§4.1). |
| 3 | API Gatekeeper | `ApiGatekeeper.execute()` wraps every YouTube net call (§4.1). |
| 4 | Rate-limit config | `config/rate_limits.json` versioned; read by `RateLimiter` (§6.2). |
| 5 | Queue management | `DownloadQueue` FIFO + max_depth + overflow strategy (§4.1, §6.2). |
| 6 | Version control | `version.py` 1.00; config files 1.00; startup validation (§6.5). |
| 7 | TDD | Test-first; mirror structure; mocks; happy+error (§8). |
| 8 | File size ≤150 | Module split designed so every file stays ≤150 code lines (§4). |
| 9 | Coverage ≥85% | `fail_under = 85` (§7). |
| 10 | Ruff zero violations | `[tool.ruff]` configured; CI command in §11 (§7). |
| 11 | No hardcoded values | `ConfigManager.get` everywhere; `constants.py` for true constants (§6.3). |
| 12 | Config architecture | `config/*.json` + `constants.py` + `.env` hierarchy (§6). |
| 13 | Secrets management | `.env-example`, `.gitignore`, no secret literals (§6.4). |
| 14 | uv toolchain | `pyproject.toml` + `uv.lock`; all commands via `uv` (§7). |

---

## 10. Verification Plan (end-to-end)

Automated (run from project root):
```powershell
uv sync
uv run ruff check src/ tests/
uv run pytest tests/ --cov=src --cov-report=term-missing -q
```
File-size guard (from the guideline):
```powershell
uv run python -c "import pathlib;[print(f'VIOLATION {f} {c}') for f in pathlib.Path('src').rglob('*.py') for c in [sum(1 for l in f.read_text(encoding='utf-8',errors='ignore').splitlines() if l.strip() and not l.strip().startswith('#'))] if c>150]"
```
Manual smoke test (short public / Creative-Commons video):
```powershell
uv run python -m ytdl "<URL>" --video --audio --subs -o .\downloads -n sample --resolution 720
# Expect: .\downloads\sample.mp4, sample.mp3, sample.en.srt
```

---

## 11. Future / Out of Scope (v-next)

- **Batch / playlist CLI surface** — the engine + queue already support it; only a CLI mode is missing.
- **Subtitle translation** and multi-language subtitle download.
- **GPU-accelerated transcription** of downloaded audio — would integrate `youtube-transcript-api` (per the
  Segal corpus) and, if local Whisper transcription is added, **reference**
  `C:\25D\GeneralLearning\transcribe-video\cuda_libs` **in place** (never copied) by prepending it to `PATH`
  before importing the CUDA-backed library, exactly as transcribe-video's `transcribe.py` does. This is the
  *only* place GPU/CUDA would enter the project, and it is explicitly **out of scope for v1.00**.
```python
# Future-only pattern (NOT used in v1.00):
import os
from pathlib import Path
CUDA_LIBS = Path(r"C:\25D\GeneralLearning\transcribe-video\cuda_libs")
os.environ["PATH"] = str(CUDA_LIBS) + os.pathsep + os.environ.get("PATH", "")
```
