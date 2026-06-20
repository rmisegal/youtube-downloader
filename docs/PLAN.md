# Implementation Plan — YouTube Downloader (Python CLI)

**PRD Source:** `docs/PRD.md`
**Plan Version:** 1.01
**Created:** 2026-06-20
**Owner:** rmisegal@gmail.com
**Execution Mode:** Interactive (executing agents may pause for clarification)

---

## 1. Executive Summary

Build a Windows-PowerShell Python CLI that, from a single YouTube URL, can download the video as **mp4**,
extract audio as **mp3**, and/or download subtitles as **`.srt`** — in any combination — into a chosen output
folder and base file name. The engine is **`yt-dlp`** (validated by Dr. Segal's knowledge graph) with FFmpeg
supplied by **`imageio-ffmpeg`** (no system FFmpeg, no GPU). The codebase is built SDK-first with strict
adherence to all 14 `/glb-quality-code-guidlines` rules, enforced as explicit phase gates.

---

## 2. Scope & Success Criteria

### In scope (PRD §1.1, §3)
- Single-URL download of any combination of mp4 / mp3 / `.srt`.
- CLI flags: `--video`, `--audio`, `--subs`, `-o/--output-dir`, `-n/--name`, `--resolution`, `--sub-lang`, `--version`.
- Best-quality video with optional height cap; subtitles manual+auto in SRT, default language `en`.
- Runs on Windows PowerShell with no system FFmpeg install and no GPU (PRD §1.3).

### Out of scope (PRD §1.4, §11)
- GUI / web service; playlist/channel CLI surface; DRM / age-gate / login bypass.
- GPU-accelerated transcription and `youtube-transcript-api` integration (future only; PRD §11).

### Success metrics (PRD §1.3)
- S1: One invocation yields the requested combination of `sample.mp4`, `sample.mp3`, `sample.<lang>.srt`.
- S2: Works on PowerShell, no system FFmpeg, no GPU.
- S3: Passes the full 14-rule glb-quality audit (see §10).

---

## 3. Assumptions, Constraints, Risks

| ID | Type | Statement | Source (PRD ref) | Mitigation |
|----|------|-----------|------------------|------------|
| A1 | Assumption | Target videos are public (no auth); optional cookies/proxy via `.env`. | §6.4 | `.env-example` placeholders; document cookies usage. |
| A2 | Assumption | `python -m ytdl` runs via the `src/main.py` shim with the package importable under uv. | §4 tree | Configure package discovery in `pyproject.toml`; verify in Phase 2 gate. |
| C1 | Constraint | Every Python file ≤ 150 code lines. | §4, Rule 8 | Module split designed up front (§5 Phase plan); file-size gate each phase. |
| C2 | Constraint | uv only — no pip / requirements.txt. | §7, Rule 14 | Phase 2 gate scans for violations. |
| C3 | Constraint | No GPU/CUDA in v1.00. | §2, §11 | No CUDA-backed imports; documented future-only pattern. |
| R1 | Risk | `yt-dlp`/YouTube format changes break downloads. | §2 | Pin `yt-dlp` in `uv.lock`; retry/backoff in gatekeeper; smoke test in Phase 11. |
| R2 | Risk | Subtitle conversion to SRT fails when only auto-captions exist. | §3.2, §5 | `FFmpegSubtitlesConvertor` + manual+auto fallback; unit test both paths. |
| R3 | Risk | Combined modes re-fetch the video multiple times. | §5 | Resolve info once; build union of post-processors (Phase 6). |
| R4 | Risk | Future D: graph re-consult hangs if drive absent. | §2 | `Test-Path D:\` guard mandated in any future task (out of scope v1.00). |

---

## 4. Quality Gate Anchors (glb-quality-code-guidlines)

| # | Rule | Primary Anchor Phase |
|---|------|----------------------|
| 1 | SDK-Oriented Architecture | Phase 4, Phase 6, Phase 7 |
| 2 | OOP / No Duplication | Phase 4, Phase 5, Review |
| 3 | API Gatekeeper with Rate Control | Phase 4 |
| 4 | Rate Limitation Configuration | Phase 3 |
| 5 | Queue Management for Overflow | Phase 4 |
| 6 | Global Version Control | Phase 2 |
| 7 | TDD Workflow | Phases 3–7, Phase 8 |
| 8 | File Size ≤ 150 LOC | Phases 2–7 |
| 9 | Coverage ≥ 85% | Phase 8 |
| 10 | Ruff Zero Violations | Phases 2–7 |
| 11 | No Hardcoded Values | Phase 3, Review |
| 12 | Configuration Architecture | Phase 3 |
| 13 | Security & Secrets | Phase 9 |
| 14 | uv Package Manager | Phase 2 |

Detailed enforcement and automated checks: §10.

---

## 5. Phase Plan

> **Standing gate (applies to every implementation phase 2–7):**
> `uv run ruff check src/ tests/` → 0 violations (Rule 10) ·
> file-size script → 0 files > 150 LOC (Rule 8) ·
> tests written before/with code, all passing (Rule 7).

### Phase 1 — Planning & Discovery
- **Objective:** Lock the requirements inventory and confirm reuse decisions before any code.
- **PRD refs:** §1, §2, §3 (all). **Rules:** none (planning).
- **Steps:**
  1.1 Confirm Requirements Inventory R1–R43 (see §9) is complete and unambiguous.
  1.2 Confirm engine = `yt-dlp`, FFmpeg = `imageio-ffmpeg`, no GPU (PRD §2).
  1.3 Confirm no Open Questions remain (§8).
- **Phase Gate:**
  - [ ] Functional: every PRD atomic demand has an inventory ID (§9).
  - [ ] Quality: 14-rule anchor table reviewed (§4).
  - [ ] Automated: n/a.

### Phase 2 — Initialization (uv, versioning, project structure) — Rules 6, 14, 8, 10
- **Objective:** Stand up the `src/` skeleton, uv toolchain, and version markers.
- **PRD refs:** §4 (tree), §6.5, §7. **Inventory:** R23, R34, R35, R36.
- **Steps:**
  2.1 `uv init`; author `pyproject.toml` (name, version `1.00`, `requires-python>=3.10`, package discovery for `src/ytdl`, `[project.scripts]`/`-m` entry). (R35, R23)
  2.2 `uv add yt-dlp imageio-ffmpeg`; `uv add --dev pytest pytest-cov ruff`; commit `uv.lock`. (R36)
  2.3 Add `[tool.ruff]` (line-length 100; select `E,F,W,I,N,UP,B,C4,SIM`; ignore `E501`), `[tool.coverage.run]` (source `src`, omit `src/main.py`), `[tool.coverage.report]` (`fail_under = 85`). (R37 prep, R38 prep)
  2.4 Create directory skeleton per §4 with empty modules + `__init__.py`; add `src/ytdl/shared/version.py` → `__version__ = "1.00"`. (R23, R34)
  2.5 Create `.gitignore` (`.env`, `cookies.txt`, `*.key`, `*.pem`, `downloads/`). (R33 prep)
- **Phase Gate:**
  - [ ] Functional: `uv sync` succeeds; `uv run python -c "import ytdl"` works.
  - [ ] Quality: `uv.lock` present, no `requirements.txt` (Rule 14); `version.py` = `1.00` (Rule 6); files ≤150 LOC (Rule 8); ruff clean (Rule 10).
  - [ ] Automated: `uv run ruff check src/`; uv-toolchain scan from guideline §AUTOMATED.

### Phase 3 — Configuration & Secrets — Rules 4, 6, 11, 12, 13, 7
- **Objective:** Externalize all tunables; version + validate config; provide secret placeholders.
- **PRD refs:** §6. **Inventory:** R27, R30, R31, R32, R33, R34.
- **Steps (TDD — tests first):**
  3.1 Write tests for `ConfigManager` (load JSON, `get("a.b", default)`, missing-key default, version validation raises `ConfigVersionError`). (R32, R34)
  3.2 Implement `config/setup.json` (version 1.00; keys per PRD §6.1) and `config/rate_limits.json` (version 1.00; `services.youtube`, `default`, `queue` per §6.2). (R30, R31)
  3.3 Implement `shared/config.py` `ConfigManager` + `SUPPORTED_CONFIG_VERSIONS=["1.00"]` validation. (R32, R34)
  3.4 Implement `constants.py` (supported extensions, mode names, format/outtmpl templates only — true constants). (R32)
  3.5 Create `.env-example` (`YTDL_PROXY=`, `YTDL_COOKIES_FILE=`). (R33)
- **Phase Gate:**
  - [ ] Functional: configs load; version mismatch rejected; defaults returned for absent keys.
  - [ ] Quality: no hardcoded tunables in source (Rule 11); config hierarchy present (Rule 12); rate limits in config not code (Rule 4); `.env-example` present, no secret literals (Rule 13); both configs versioned (Rule 6).
  - [ ] Automated: `uv run pytest tests/unit/shared/test_config.py`; secret-scan script; `.env-example` existence check.

### Phase 4 — Architecture & Shared Infrastructure — Rules 1, 2, 3, 5, 7, 8, 10
- **Objective:** Build the gatekeeper / rate limiter / queue and the yt-dlp/ffmpeg infra layer.
- **PRD refs:** §4.1, §5, §6.2. **Inventory:** R20, R26, R27, R28, R25 (base scaffolding).
- **Steps (TDD — tests first, all external boundaries mocked):**
  4.1 `shared/rate_limit.py` `RateLimiter` (sliding-window/token-bucket; limits from config). (R27)
  4.2 `shared/queue.py` `DownloadQueue` (FIFO, `max_depth`, drain, `overflow_strategy`). (R28)
  4.3 `shared/gatekeeper.py` `ApiGatekeeper.execute(callable, ...)` → rate check → retry/backoff (`max_retries`, `retry_after_seconds`) → logging → queue overflow. (R26)
  4.4 `infra/ffmpeg.py` `FfmpegLocator` wrapping `imageio_ffmpeg.get_ffmpeg_exe()` — exposes `exe()` (full path; yt-dlp `ffmpeg_location` needs the file, not the dir, because the imageio binary is not named `ffmpeg.exe`) and `exe_dir()`. (R20)
  4.5 `infra/ytdlp_client.py` thin `yt_dlp.YoutubeDL` wrapper; **all** `extract_info`/`download` calls routed through `ApiGatekeeper`. (R26)
  4.6 `services/base.py` `BaseDownloader` — shared ydl-opts builder, `outtmpl`, `ffmpeg_location` wiring (single source for subclasses). (R25)
  4.7 Consume optional `YTDL_PROXY` → yt-dlp `proxy` and `YTDL_COOKIES_FILE` → yt-dlp `cookiefile` from environment; omit each when unset. (R44, PRD §2 A1/§6.4, Rule 11)
- **Phase Gate:**
  - [ ] Functional: rate limit enforced; overflow queued (not crashed); retries on transient error; no direct yt-dlp net call bypasses gatekeeper.
  - [ ] Functional: proxy/cookies injected only from env when set, omitted when unset (R44, PRD §6.4).
  - [ ] Quality: gatekeeper centralizes all API calls (Rule 3); queue overflow handled (Rule 5); `BaseDownloader` removes duplication (Rule 2); infra reachable only via services/SDK (Rule 1); files ≤150 (Rule 8); ruff clean (Rule 10); tests first (Rule 7).
  - [ ] Automated: `uv run pytest tests/unit/shared tests/unit/infra`; grep for `YoutubeDL(`/`requests.` outside `infra/` = none.

### Phase 5 — Domain Implementation (Video / Audio / Subtitles / Metadata) — Rules 2, 7, 8, 10
- **Objective:** Implement the three downloader services + metadata, each subclassing `BaseDownloader`.
- **PRD refs:** §3.2, §5. **Inventory:** R2, R3, R4, R11, R20, R25, R29.
- **Steps (TDD — tests first):**
  5.1 `services/metadata.py` — resolve info dict / title for filename templating. (R12 prep)
  5.2 `services/video.py` `VideoDownloader` — `format="bv*[height<=RES]+ba/b"`, `merge_output_format="mp4"`. (R2, R8)
  5.3 `services/audio.py` `AudioDownloader` — `FFmpegExtractAudio` (codec/quality from config). (R3)
  5.4 `services/subtitles.py` `SubtitleDownloader` — `writesubtitles`+`writeautomaticsub`, `subtitleslangs=[lang]`, `subtitlesformat="srt"` + `FFmpegSubtitlesConvertor` → `<name>.<lang>.srt`. (R4, R11-naming)
- **Phase Gate:**
  - [ ] Functional (mocked): each service builds correct ydl-opts; subtitle convertor guarantees `.srt`; manual+auto path covered.
  - [ ] Quality: subclasses override only specifics, no duplicated opts logic (Rule 2); each file ≤150 (Rule 8); ruff clean (Rule 10); tests cover happy+error (Rule 7).
  - [ ] Automated: `uv run pytest tests/unit/services`.

### Phase 6 — SDK / API Surface — Rules 1, 2, 7
- **Objective:** Expose every operation through `YoutubeDownloaderSDK`; fetch-once for combined modes.
- **PRD refs:** §4.1, §5. **Inventory:** R5, R12, R24.
- **Steps (TDD — tests first):**
  6.1 `sdk/sdk.py` `YoutubeDownloaderSDK` with methods: `download(url, modes, output_dir, name, resolution, sub_lang)` plus per-mode methods. (R24)
  6.2 Implement combinability: resolve info once, build the **union** of post-processors when multiple modes requested; default to `video` when none. (R5, R12)
  6.3 Ensure SDK is the only object external layers import (no internal leakage). (R24, Rule 1)
- **Phase Gate:**
  - [ ] Functional: combined `--video --audio --subs` triggers a single resolve + union post-processing; default-video honored.
  - [ ] Quality: all business ops reachable via SDK without importing internals (Rule 1); no duplication (Rule 2); tests first (Rule 7).
  - [ ] Automated: `uv run pytest tests/unit/sdk`.

### Phase 7 — CLI / External Interface — Rules 1, 7, 8, 10
- **Objective:** argparse CLI that delegates 100% to the SDK; behavioral requirements.
- **PRD refs:** §3.1, §3.3. **Inventory:** R1, R5, R6, R7, R8, R9, R10, R13, R14, R15, R16, R17.
- **Steps (TDD — tests first):**
  7.1 `cli/main.py` argparse: positional `url`; flags `--video/--audio/--subs`, `-o/--output-dir`, `-n/--name`, `--resolution`, `--sub-lang`, `--version`. (R1, R6–R10)
  7.2 Default-to-video when no output flag; combinable toggles. (R5)
  7.3 UTF-8 stdout reconfig; structured progress logging per phase. (R13, R14)
  7.4 Output dir created idempotently; non-interactive; deterministic exit codes — non-zero on invalid URL, **network failure after retries**, **unsupported request**, and config-version mismatch. (R15, R16, R17, PRD §3.3)
  7.5 `src/main.py` shim for `python -m ytdl` → `cli.main`. (A2)
- **Phase Gate:**
  - [ ] Functional: all flags parse; `--version` prints code+config version; missing dir auto-created; non-zero exit on **all four** conditions — invalid URL, network failure after retries, unsupported request, config-version mismatch (PRD §3.3).
  - [ ] Quality: zero business logic in CLI — delegates to SDK (Rule 1); files ≤150 (Rule 8); ruff clean (Rule 10); tests first (Rule 7).
  - [ ] Automated: `uv run pytest tests/unit/cli`.

### Phase 8 — Testing & Coverage — Rules 7, 9
- **Objective:** Prove ≥85% coverage with all boundaries mocked.
- **PRD refs:** §8. **Inventory:** R38, R39.
- **Steps:**
  8.1 `tests/conftest.py` fixtures: `mock_ytdl`, mock `imageio_ffmpeg`/`subprocess`, `sample_config`, `tmp_output_dir`. (R39)
  8.2 Fill error-path tests (invalid URL, empty/`None` args, overflow→queued, version mismatch). (R39)
  8.3 Run coverage; raise to ≥85%; test files also ≤150 LOC. (R38, Rule 8)
- **Phase Gate:**
  - [ ] Functional: full suite green; no network / no real ffmpeg invoked.
  - [ ] Quality: coverage ≥85% enforced by `fail_under` (Rule 9); happy+error per public method (Rule 7).
  - [ ] Automated: `uv run pytest tests/ --cov=src --cov-report=term-missing`.

### Phase 9 — Security Review — Rule 13
- **Objective:** Verify no secrets in source; secret hygiene complete.
- **PRD refs:** §6.4. **Inventory:** R33.
- **Steps:**
  9.1 Run secret-scan; confirm no API keys/tokens/passwords in source.
  9.2 Confirm `.env`, `cookies.txt`, `*.key`, `*.pem` git-ignored; `.env-example` committed with placeholders only.
- **Phase Gate:**
  - [ ] Functional: optional proxy/cookies read from env, never hardcoded.
  - [ ] Quality: secret scan clean; `.env-example` present (Rule 13).
  - [ ] Automated: secret-scan script from guideline §AUTOMATED; `.gitignore` check.

### Phase 10 — Documentation & Deliverables
- **Objective:** Ship README + keep PRD/PLAN authoritative; record future scope.
- **PRD refs:** §4 tree, §11. **Inventory:** R41, R43, R14 (docs).
- **Steps:**
  10.1 `README.md`: install (`uv sync`), PowerShell usage examples, flags table, config overview.
  10.2 Confirm `docs/PRD.md` + `docs/PLAN.md` in repo; document future GPU/transcription pattern (cuda_libs in place, never copied). (R43)
- **Phase Gate:**
  - [ ] Functional: README commands run as written.
  - [ ] Quality: docs reference uv-only commands (Rule 14).
  - [ ] Automated: n/a (manual doc review).

### Phase 11 — Release & Verification (final gate) — all 14 rules + all ACs
- **Objective:** Prove S1–S3 and full quality compliance end-to-end.
- **PRD refs:** §1.3, §10. **Inventory:** R18, R40, R42, all ACs.
- **Steps:**
  11.1 Run the full automated suite (§10 commands).
  11.2 Manual smoke test (PowerShell, short public/CC video):
  `uv run python -m ytdl "<URL>" --video --audio --subs -o .\downloads -n sample --resolution 720`
  → verify `sample.mp4`, `sample.mp3`, `sample.en.srt`. (R18, S1)
  11.3 Confirm non-goals respected (no GUI/web, no playlist CLI, no DRM bypass). (R40)
  11.4 Complete Sign-Off table (§11) and Quality Verification Matrix (§10).
- **Phase Gate:**
  - [ ] Functional: S1–S3 met; smoke artifacts present and valid.
  - [ ] Quality: 14/14 rules PASS (§10); 100% PRD coverage (§9).
  - [ ] Automated: `uv sync` · `uv run ruff check src/ tests/` · `uv run pytest tests/ --cov=src` · file-size script · secret-scan.

---

## 6. Deliverables

| Deliverable | Producing Phase |
|-------------|-----------------|
| `pyproject.toml` + `uv.lock` + `src/ytdl` skeleton + `version.py` | Phase 2 |
| `config/setup.json`, `config/rate_limits.json`, `.env-example`, `constants.py`, `ConfigManager` | Phase 3 |
| `gatekeeper.py`, `rate_limit.py`, `queue.py`, `infra/ffmpeg.py`, `infra/ytdlp_client.py`, `services/base.py` | Phase 4 |
| `services/video.py`, `audio.py`, `subtitles.py`, `metadata.py` | Phase 5 |
| `sdk/sdk.py` (`YoutubeDownloaderSDK`) | Phase 6 |
| `cli/main.py`, `src/main.py` | Phase 7 |
| `tests/` suite ≥85% coverage | Phase 8 |
| `README.md` + authoritative `docs/PRD.md`, `docs/PLAN.md` | Phase 10 |
| Smoke-test evidence + Sign-Off | Phase 11 |

---

## 7. Dependencies & External Integrations

| Dependency | Type | Used In Phase |
|------------|------|---------------|
| `yt-dlp` | runtime (download engine) | Phases 4–6 |
| `imageio-ffmpeg` | runtime (FFmpeg binary) | Phases 4–5 |
| `pytest`, `pytest-cov`, `ruff` | dev/test | Phases 2–8 |
| `uv` | toolchain | Phases 2–11 |
| YouTube (external service) | network | Phases 4, 11 |

---

## 8. Open Questions

_None._ The PRD is fully specified; all design decisions (engine, FFmpeg source, no-GPU, mode combinability,
subtitle format/language, quality control, full 14-rule compliance) were resolved during PRD authoring. The
only implementation detail noted (A2: `python -m ytdl` package discovery) is resolved in Phase 2 and is not a
material ambiguity.

---

## 9. PRD Coverage Matrix

| PRD Ref | Atomic Demand | Type | Primary Phase | Secondary | Verification Step |
|---------|---------------|------|---------------|-----------|-------------------|
| §3.1 (R1) | `url` positional required | Func | 7 | 6 | 7.1 |
| §3.1/§3.2 (R2) | `--video` → best mp4 merged | Func | 5 | 6,7 | 5.2 |
| §3.1/§3.2 (R3) | `--audio` → mp3 | Func | 5 | 6,7 | 5.3 |
| §3.1/§3.2 (R4) | `--subs` → srt manual+auto | Func | 5 | 6,7 | 5.4 |
| §3.1 (R5) | Outputs combinable; default video | Func | 6 | 7 | 6.2 |
| §3.1/§3.3 (R6) | `-o` dir, default `./downloads`, auto-create | Func | 7 | 3 | 7.4 |
| §3.1 (R7) | `-n` name, default `%(title)s` | Func | 7 | 6 | 7.1 |
| §3.1/§3.2 (R8) | `--resolution` cap, default best | Func | 5 | 7 | 5.2 |
| §3.1 (R9) | `--sub-lang`, default `en` | Func | 7 | 5 | 7.1 |
| §3.1 (R10) | `--version` prints code+config version | Func | 7 | 2 | 7.1 |
| §3.2/§5 (R11) | `<name>.<lang>.srt`; convertor ensures srt | Func | 5 | — | 5.4 |
| §5 (R12) | Combined modes: resolve once, union PP | Func | 6 | 5 | 6.2 |
| §3.3 (R13) | UTF-8 stdout | NFR | 7 | — | 7.3 |
| §3.3 (R14) | Progress + structured logging | NFR | 7 | 10 | 7.3 |
| §3.3 (R15) | Deterministic exit codes | NFR | 7 | — | 7.4 |
| §3.3 (R16) | Idempotent output-dir creation | NFR | 7 | — | 7.4 |
| §3.3 (R17) | No interactive prompts | NFR | 7 | — | 7.4 |
| §1.3 (R18) | PowerShell, no system FFmpeg, no GPU | Constraint | 11 | 4,5 | 11.2 |
| §2 (R19) | Engine = yt-dlp | Constraint | 4 | 5,6 | 4.5 |
| §2/§5 (R20) | FFmpeg via imageio-ffmpeg `ffmpeg_location` | Constraint | 4 | 5 | 4.4 |
| §2/§11 (R21) | No GPU in v1.00 | Constraint | 1 | 11 | 1.2 |
| §2 (R22) | D: drive-safety on future graph re-consult | Risk | 10 | — | 10.2 (R4 risk) |
| §4 (R23) | `src/` layout, package `ytdl` | Arch | 2 | — | 2.4 |
| §4.1 (R24) | SDK single entry; CLI delegates | Arch (R1) | 6 | 7 | 6.1/6.3 |
| §4.1 (R25) | `BaseDownloader` inheritance, no dup | Arch (R2) | 4 | 5 | 4.6 |
| §4.1 (R26) | `ApiGatekeeper` wraps every net call | Arch (R3) | 4 | — | 4.3/4.5 |
| §4.1/§6.2 (R27) | `RateLimiter` from `rate_limits.json` | Arch (R4) | 4 | 3 | 4.1 |
| §4.1/§6.2 (R28) | `DownloadQueue` FIFO/max_depth/overflow | Arch (R5) | 4 | — | 4.2 |
| §4 (R29) | Every file ≤150 LOC | Arch (R8) | 2–7 | — | standing gate |
| §6.1 (R30) | `setup.json` v1.00 with keys | Config | 3 | — | 3.2 |
| §6.2 (R31) | `rate_limits.json` v1.00 services/default/queue | Config | 3 | 4 | 3.2 |
| §6.3 (R32) | No hardcoded values; `constants.py` true constants | Config (R11) | 3 | Review | 3.3/3.4 |
| §6.4 (R33) | `.env-example` + `.gitignore` secrets | Security (R13) | 9 | 2,3 | 9.2 |
| §6.5 (R34) | `version.py`=1.00; config version validation | Config (R6) | 2 | 3 | 2.4/3.3 |
| §7 (R35) | uv only, `uv.lock`, no requirements.txt, py3.10+ | Tool (R14) | 2 | — | 2.1/2.2 |
| §7 (R36) | deps yt-dlp, imageio-ffmpeg; dev pytest/cov/ruff | Tool | 2 | — | 2.2 |
| §7 (R37) | ruff config + zero violations | Quality (R10) | 2 | 2–7 | standing gate |
| §7/§8 (R38) | coverage `fail_under=85` | Quality (R9) | 8 | 2 | 8.3 |
| §8 (R39) | TDD, mirror tests, mock boundaries, happy+error, fixtures | Test (R7) | 8 | 3–7 | 8.1/8.2 |
| §1.4 (R40) | Non-goals respected | Constraint | 11 | — | 11.3 |
| §4 tree (R41) | PRD doc in `docs/` | Deliverable | 10 | — | 10.2 |
| §10 (R42) | Verification plan commands | Deliverable | 11 | 8 | 11.1 |
| §11 (R43) | Future out-of-scope documented incl cuda_libs in-place | Deliverable | 10 | — | 10.2 |
| §2 A1/§6.4 (R44) | Consume optional `YTDL_PROXY`/`YTDL_COOKIES_FILE` from env into yt-dlp opts | Func/NFR | 4 | 9 | 4.7 |

**Coverage: 44/44 atomic demands mapped (100%).**

> **Changelog**
> - **1.01 (2026-06-20):** Audit back-propagation (`/new:todo-vs-prd`). Added R44 (consume
>   `YTDL_PROXY`/`YTDL_COOKIES_FILE` from env) as Phase 4.7 + gate; enumerated all four exit-code
>   conditions in Phase 7.4 + gate (PRD §3.3).
> - **1.00 (2026-06-20):** Initial plan derived from `docs/PRD.md`.

---

## 10. Quality Verification Matrix (14 Rules)

| Rule # | Rule | Enforced In Phase(s) | Verification Method | Automated Check |
|--------|------|----------------------|---------------------|-----------------|
| 1 | SDK-Oriented Architecture | 4, 6, 7 | CLI/SDK import boundary; all ops via SDK | grep: no internal imports in `cli/`; `YoutubeDL(` only in `infra/` |
| 2 | OOP / No Duplication | 4, 5, Review | `BaseDownloader` + subclasses; single opts builder | code review; duplication scan |
| 3 | API Gatekeeper | 4 | All net calls via `ApiGatekeeper.execute` | grep for direct `extract_info`/`download` outside gatekeeper path |
| 4 | Rate-Limit Config | 3 | Limits in `rate_limits.json`, read by `RateLimiter` | `pytest tests/unit/shared/test_rate_limit.py`; no rate constants in code |
| 5 | Queue Management | 4 | FIFO + max_depth + overflow strategy | `pytest tests/unit/shared/test_queue.py` (overflow→queued) |
| 6 | Version Control | 2 | `version.py`=1.00; configs versioned + validated | `pytest` version-validation test; grep configs for `"version"` |
| 7 | TDD Workflow | 3–8 | Tests first; happy+error per public method | `uv run pytest tests/` |
| 8 | File Size ≤150 | 2–7 | Module split by design | file-size script (0 violations) |
| 9 | Coverage ≥85% | 8 | `fail_under=85` | `uv run pytest --cov=src` |
| 10 | Ruff Zero Violations | 2–7 | ruff config active | `uv run ruff check src/ tests/` |
| 11 | No Hardcoded Values | 3, Review | `ConfigManager.get` everywhere | code review; grep for literal paths/limits |
| 12 | Config Architecture | 3 | `config/*.json` + `constants.py` + `.env` hierarchy | structure check |
| 13 | Security & Secrets | 9 | `.env-example`; no secret literals | secret-scan; `.env-example` existence check |
| 14 | uv Package Manager | 2 | `pyproject.toml`+`uv.lock`; no pip | uv-toolchain scan; no `requirements.txt` |

**All 14 rules enforced (14/14).**

---

## 11. Sign-Off

| Check | Status | Evidence |
|-------|--------|----------|
| 100% PRD coverage | PASS | §9 (44/44) |
| 14/14 rules enforced | PASS | §10 |
| No open questions | PASS | §8 (none) |
| All phase gates defined | PASS | §5 (Phases 1–11) |
