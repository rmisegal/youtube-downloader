# PRD — Dynamic Video Mixer & Player Extension (Python CLI)

| Field | Value |
|-------|-------|
| Project | `youtube-downloader` (Video Mixer & Player Extension) |
| Location | `C:\25D\app\youtube-downloader` |
| Repository | https://github.com/rmisegal/youtube-downloader (public) |
| Document version | 1.02 |
| Code version (target) | 1.02 |
| Config version (target) | 1.02 |
| Date | 2026-06-20 |
| Author | Generated for rmisegal@gmail.com |
| Status | Approved — ready for extension implementation |
| Builds on | `docs/PRD.md` (base downloader) · `docs/PLAN.md` · `docs/TODO.md` |

---

## 1. Overview & Goals

### 1.1 Purpose
This PRD defines an interactive, real-time **VJ (Video Jockey) playback engine** layered onto the existing
`youtube-downloader`. It sequences local and downloaded videos into a continuous loop with seamless
**crossfade transitions** of video frames and audio, driven from Windows PowerShell. It reuses the project's
architecture — `uv`, `imageio-ffmpeg` for the bundled FFmpeg binary, `DownloadQueue`, `ConfigManager`, and the
rate-limited `ApiGatekeeper` download path — so downloaded content and local media feed one playback pipeline.

### 1.2 One-sentence scope
> `uv run python -m ytdl --mix --dir "<PATH>" [--mode option1|option2] [--selection random|manual] [--crossfade-time N]`

### 1.3 Core capabilities
1. **Dual engine architecture** (selectable at runtime):
   - **Option 1 — FFmpeg→VLC streaming server (TRUE crossfade):** a live composite stream built by an
     FFmpeg subprocess (`xfade` video + `acrossfade` audio) piped continuously as `mpegts` into a single
     standalone VLC instance (`vlc -`). This is the engine that delivers real per-frame video+audio crossfade.
   - **Option 2 — Dual-libVLC player matrix (gapless switching):** two `python-vlc` players double-buffered
     for gapless track handoff with an **audio** volume crossfade. *(Per-pixel video alpha blending across two
     libVLC windows is a documented libVLC limitation — see §4.3.2 and §8; not promised in v1.02.)*
2. **Dynamic live queue:** queue a local folder, hot-append local files, or inject YouTube URLs mid-playback
   (downloaded via the existing SDK → gatekeeper, then enqueued).
3. **Smart selection:** randomized infinite shuffle (Autopilot) or manual numbered curation.

### 1.4 Success criteria
- S1: `--mix --dir <folder>` plays the folder's videos back-to-back with crossfades, looping indefinitely.
- S2: Both engines run on Windows PowerShell using the bundled FFmpeg + an installed VLC; no GPU required.
- S3: Passes the full `/glb-quality-code-guidlines` audit (all 14 rules) — see §9.

### 1.5 Non-goals
- No GUI control surface (keyboard/mouse VJ deck); CLI + console prompts only.
- No true per-pixel video alpha crossfade in Option 2 (libVLC limitation).
- No seeking, multi-monitor management, or hardware-acceleration tuning.
- No DRM circumvention; YouTube injection obeys the existing rate-limit guards.

---

## 2. Architecture & Layering

The extension integrates into the existing decoupled SDK layout; **every Python file stays ≤150 code lines**.

```
CLI (argparse) ─► YoutubeDownloaderSDK ─► services/mixer/   (MixerService, PlaylistEngine)
                                       ├► infra/playback/    (StreamServer, LibVlcPlayerMatrix, VlcLocator)
                                       └► shared             (DownloadQueue, ConfigManager, ApiGatekeeper)
```

- **SDK entry points (Rule 1):** `src/ytdl/sdk/sdk.py` gains `mix_local_directory(dir, *, mode, selection,
  crossfade)` and `stream_live_queue(...)`. The CLI parses args and delegates; **no business logic in the CLI**.
- **New packages (each with `__init__.py`):**
  - `src/ytdl/services/mixer/` — `MixerService` (orchestration) and `PlaylistEngine` (random/manual queue
    building + live insertion). Split across small files to honor the 150-line rule.
  - `src/ytdl/infra/playback/` — `StreamServer` (Option 1), `LibVlcPlayerMatrix` (Option 2), `VlcLocator`
    (detect the `vlc` binary / libVLC).
- **Reuse — do not reinvent:**
  - `FfmpegLocator` (`src/ytdl/infra/ffmpeg.py`) → bundled FFmpeg path for Option 1.
  - `DownloadQueue` (`src/ytdl/shared/queue.py`) → FIFO playback queue.
  - `ConfigManager` (`src/ytdl/shared/config.py`) → all playback tunables.
  - `SDK.download` + `ApiGatekeeper` (existing) → when a YouTube URL is hot-injected, it is downloaded to the
    cache dir through the rate-limited path, then enqueued. Playback never bypasses the throttle/quota guards.
  - `parse_selection` (`src/ytdl/cli/playlist.py`) → reuse for the manual numbered picker.
- **Constants:** add `SUPPORTED_VIDEO_FORMATS: tuple = (".mp4", ".mkv", ".mov", ".avi")` to `constants.py`.

---

## 3. Functional Requirements — CLI Contract

Extends the existing `argparse` builder (`src/ytdl/cli/args.py`); dispatched from `src/ytdl/cli/main.py`.

```powershell
uv run python -m ytdl --mix --dir "<PATH>" [--mode option1|option2] [--selection random|manual] [--crossfade-time N]
```

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--mix` | flag | off | Switch from download mode to live mixer/player mode. |
| `--dir` | path | **required with `--mix`** | Folder of local video assets (absolute or relative). |
| `--mode` | str | `option2` (config `playback.default_mode`) | `option1` (FFmpeg→VLC stream, true crossfade) or `option2` (dual-libVLC gapless). |
| `--selection` | str | `random` (config `playback.default_selection`) | `random` (infinite shuffle) or `manual` (numbered picker). |
| `--crossfade-time` | int | `3` (config `playback.crossfade_duration_seconds`) | Crossfade overlap window in seconds. |

`--mix` is mutually independent from the download flags; when `--mix` is present the download flags are ignored
(the SDK routes to the mixer). `--dir` is required in mix mode (missing → usage error, **exit 2**).

---

## 4. Behavioral Specification

### 4.1 Folder scan & asset discovery
- **Validation:** resolve `--dir`. **Removable-drive safety (per global rule):** if the path is under `D:\`
  or `H:\`, run a `Test-Path`/existence check FIRST and exit clearly if the volume is not mounted — never
  block on a missing removable/network drive. An unreachable/empty directory logs a clear warning and exits
  with **code 2**.
- **Format sniffing:** index files whose extension is in the immutable `SUPPORTED_VIDEO_FORMATS` tuple
  (`constants.py`). Non-media files are ignored.

### 4.2 Selection & queue workflows
- **`--selection random` (Autopilot):** populate the `DownloadQueue` with a shuffled set of discovered
  tracks; as the queue nears exhaustion, automatically re-scan the directory and refill → uninterrupted loop.
- **`--selection manual`:**
  1. Print a clean numbered inventory of discovered media to the console.
  2. Prompt for a comma-separated sequence (e.g. `1, 4, 2, 5`; ranges like `2-4` supported) — parsed via the
     existing `parse_selection` helper.
  3. Build a FIFO playback queue from the chosen order.
  4. **Live insertion:** while a track plays, the engine keeps listening for auxiliary input, allowing the
     operator to hot-append a local file path or a YouTube URL into the active deck. YouTube URLs are fetched
     through `SDK.download` (rate-limited) into the cache dir, then enqueued. Interactive prompts gracefully
     no-op on non-TTY/EOF (consistent with the playlist picker).

### 4.3 Engine execution modes

#### 4.3.1 Option 1 — Live FFmpeg→VLC streaming server (TRUE crossfade)
- A background worker launches an FFmpeg subprocess using the bundled binary (`FfmpegLocator`).
- It consumes sequential tracks from the FIFO queue, joining video with the `xfade` filter
  (`transition=fade`, offset derived from track duration − `crossfade-time`) and audio with `acrossfade`.
- The composite is muxed as `mpegts` and written to the **stdin** of a standalone `vlc -` process.
- **Result:** VLC plays an un-seekable, infinite live broadcast with no black frame or load gap between tracks.
- *Implementation note (risk):* continuous `xfade` across an arbitrary, growing FIFO requires careful pipeline
  construction (pairwise overlap with correct offsets, or a rolling two-input concat). See §10.

#### 4.3.2 Option 2 — Dual-libVLC player matrix (gapless switching)
- Create two `python-vlc` players (`Player_A`, `Player_B`). While A displays the current track, B silently
  pre-loads the next track (muted, hidden).
- A polling loop tracks remaining runtime; when it reaches `crossfade-time`, the decks hand off with an
  **audio** volume crossfade (A: 100→0, B: 0→100) plus a window-overlap visual handoff; then A stops and
  becomes the background buffer for the subsequent track.
- **Limitation (documented, not a defect):** libVLC does not natively alpha-composite two independent video
  windows, so Option 2 provides **gapless switching with audio crossfade**, not per-pixel video blending. For
  true video+audio frame crossfade, use Option 1.

---

## 5. Configuration (version 1.02)

### 5.1 `config/setup.json` additions
```json
{
  "version": "1.02",
  "playback": {
    "default_mode": "option2",
    "default_selection": "random",
    "crossfade_duration_seconds": 3,
    "supported_video_formats": [".mp4", ".mkv", ".mov", ".avi"]
  }
}
```
All playback tunables are read via `ConfigManager.get("playback.<key>", default)` (Rule 11). The
authoritative supported-format tuple lives in `constants.py`; the config list mirrors it for user override.

### 5.2 `config/rate_limits.json`
Bumped to `"version": "1.02"`. No new keys — a hot-injected YouTube URL is processed through the existing
`ApiGatekeeper` (throttle pacing + per-minute/hour/day/month quota), so real-time playback cannot exceed the
download safety guards.

### 5.3 Versioning
`ConfigManager.SUPPORTED_CONFIG_VERSIONS` adds `"1.02"`; `src/ytdl/shared/version.py __version__` → `"1.02"`.
Startup validation rejects unsupported versions with `ConfigVersionError` (exit 5).

---

## 6. Dependencies & Prerequisites

| Item | How | Notes |
|------|-----|-------|
| `python-vlc` | `uv add python-vlc` (Rule 14) | Python binding for libVLC (Option 2). |
| **VLC Media Player / libVLC** | **External install, required** | NOT pip-installable. Option 1 needs the `vlc` binary on PATH; Option 2 needs libVLC (shipped with VLC). |
| FFmpeg | already bundled via `imageio-ffmpeg` | Reused through `FfmpegLocator`. |

`VlcLocator` detects VLC/libVLC at startup of mix mode. If the required component is missing, the tool prints
an actionable message ("install VLC Media Player from videolan.org") and exits with **code 7**.

---

## 7. Exit Codes (extends the existing 0–6)

| Code | Meaning |
|------|---------|
| `0` | Success / clean shutdown. |
| `1` | Other / unexpected error. |
| `2` | `--dir` unreachable or missing (also argparse/usage errors). |
| `6` | Rate limit / quota reached (YouTube injection) — protects the account. |
| `7` | **VLC / playback dependency missing** (install VLC). |

(Codes 3 = network-after-retries, 4 = unsupported request, 5 = config-version mismatch carry over from the base tool.)

---

## 8. Testing & Compliance Strategy (TDD)

- **Mirrored tests:** every new module under `services/mixer/` and `infra/playback/` gets a matching
  `tests/unit/...` file; test files also ≤150 lines.
- **Mock all boundaries** (fixtures in `tests/conftest.py`): `python-vlc` (`Instance`, `MediaPlayer`, media
  states, volume/opacity calls), the FFmpeg and `vlc` **subprocess** handles, and filesystem directory scans.
  **No real window rendering, no hardware loops, no real subprocess, no network** in unit tests.
- **Determinism:** polling/timing loops take an injectable clock/sleep so tests never wait in real time
  (mirrors the `RateLimiter`/`ApiGatekeeper` pattern).
- **Gates:** `uv run ruff check` zero violations; coverage ≥85% (`fail_under`); file-size ≤150; uv-only.

---

## 9. glb-quality Compliance Matrix (all 14 rules)

| # | Rule | How the extension satisfies it |
|---|------|--------------------------------|
| 1 | SDK architecture | `mix_local_directory`/`stream_live_queue` on the SDK; CLI delegates (§2, §3). |
| 2 | OOP / no duplication | `MixerService`/`PlaylistEngine` + engine classes; reuse `DownloadQueue`, `parse_selection`, `FfmpegLocator` (§2). |
| 3 | API Gatekeeper | Hot-injected YouTube URLs go through existing `ApiGatekeeper` (§4.2). |
| 4 | Rate-limit config | Reuses `rate_limits.json` for injected downloads (§5.2). |
| 5 | Queue management | `DownloadQueue` is the FIFO playback queue; overflow strategy reused (§4.2). |
| 6 | Version control | Config + code → `1.02`; validation (§5.3). |
| 7 | TDD | Test-first; mocked VLC/FFmpeg/FS; injectable clocks (§8). |
| 8 | File size ≤150 | Mixer/playback split into small modules (§2, §8). |
| 9 | Coverage ≥85% | Enforced via existing `fail_under` (§8). |
| 10 | Ruff zero violations | Existing ruff config applies (§8). |
| 11 | No hardcoded values | Mode/selection/crossfade/formats from `playback` config (§5.1). |
| 12 | Config architecture | New `playback` block in `setup.json`; constants in `constants.py` (§5.1). |
| 13 | Secrets management | No new secrets; reuses `.env`/gitignore (§6). |
| 14 | uv package manager | `uv add python-vlc`; all commands via uv (§6). |

---

## 10. Verification Plan

Automated:
```powershell
uv sync
uv run ruff check src/ tests/
uv run pytest tests/ --cov=src --cov-report=term-missing -q
```
File-size guard (existing script) → 0 files > 150 code lines.

Manual smoke (requires VLC installed):
```powershell
uv run python -m ytdl --mix --dir ".\downloads" --mode option1 --selection random --crossfade-time 2
uv run python -m ytdl --mix --dir ".\downloads" --mode option2 --selection manual
```
Expect: a VLC window/stream plays the folder's videos back-to-back; Option 1 shows true video+audio
crossfades; Option 2 shows gapless handoff with audio crossfade; missing VLC → clear message + exit 7;
missing/unmounted `--dir` → exit 2.

---

## 11. Risks / Out of Scope (v1.02)

- **Option 1 pipeline complexity:** seamless `xfade` across an arbitrary/growing FIFO needs careful offset
  handling; a rolling two-input overlap approach is the recommended implementation path.
- **Option 2 video alpha:** true per-pixel video crossfade across two libVLC windows is not supported;
  Option 2 is gapless switching + audio crossfade by design.
- **Out of scope:** GUI VJ deck, seeking, multi-monitor, hardware-accel tuning, and live network restream.
