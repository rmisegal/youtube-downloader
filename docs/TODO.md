# TODO — YouTube Downloader (derived from PLAN.md)

**Plan source:** `docs/PLAN.md`
**Generated:** 2026-06-20
**Minimum tasks contract:** >= 200
**Total atomic tasks:** 244
**Coverage:** 44/44 PRD demands + 14/14 rules + all gates/sign-off (100%)
**Audit:** `/new:todo-vs-prd` 2026-06-20 — gaps GA.6 (proxy/cookies consumption), GA.7 (full exit-code set) closed; PLAN back-propagated to v1.01.

## Conventions
- `[ ]` = open task, `[x]` = completed.
- Every task ends with citations: `(Plan §x)`, `(Plan Phase n.m)`, `(Plan Gate n)`, `(Rule #k)`, `(Rxx)`, `(Sxx)`.
- Each phase ends with **Gate** tasks (functional + quality + automated) and a **Commit** task.
- TDD ordering: RED (failing test) → GREEN (implementation) → REFACTOR.
- `Rxx` = Requirement inventory ID from Plan §9. `Sx` = success metric from Plan §2.

---

## Phase 1 — Planning & Discovery
**Objective:** Lock requirements + reuse decisions before code. | **Plan refs:** §1–§3 | **Rules:** none

- [x] Read `docs/PRD.md` and `docs/PLAN.md` end-to-end; confirm scope understood (Plan §1)
- [x] Confirm Requirements Inventory R1–R43 is complete and unambiguous (Plan §9, Phase 1.1)
- [x] Confirm engine = `yt-dlp` per Segal knowledge graph (Plan §2, Phase 1.2)
- [x] Confirm FFmpeg source = `imageio-ffmpeg`, no system FFmpeg (Plan §2, Phase 1.2)
- [x] Confirm no GPU/CUDA in v1.00 (Plan §2/§11, R21)
- [x] Confirm Open Questions list is empty (Plan §8)
- [x] Phase 1 Gate — verify every PRD atomic demand has an inventory ID (Plan Gate 1)
- [x] Phase 1 Gate — review 14-rule anchor table (Plan §4)
- [x] Phase 1 Commit — `docs: confirm requirements inventory and reuse decisions` (Rule #6)

---

## Phase 2 — Initialization (uv, versioning, structure)
**Objective:** Stand up `src/` skeleton, uv toolchain, version markers. | **Plan refs:** §4,§6.5,§7 | **Rules:** 6,8,10,14

- [x] Run `uv init` to create the project scaffold (Plan Phase 2.1, Rule #14)
- [x] Author `pyproject.toml` `[project]` name=`youtube-downloader`, version=`1.00` (Plan Phase 2.1, R35, Rule #6)
- [x] Set `requires-python = ">=3.10"` in `pyproject.toml` (Plan Phase 2.1, R35)
- [x] Configure package discovery for `src/ytdl` (src layout) in `pyproject.toml` (Plan Phase 2.1, R23, A2)
- [x] Configure `python -m ytdl` entry (script/`__main__`) (Plan Phase 2.1, A2)
- [x] Run `uv add yt-dlp` (Plan Phase 2.2, R36, R19)
- [x] Run `uv add imageio-ffmpeg` (Plan Phase 2.2, R36, R20)
- [x] Run `uv add --dev pytest` (Plan Phase 2.2, R36)
- [x] Run `uv add --dev pytest-cov` (Plan Phase 2.2, R36)
- [x] Run `uv add --dev ruff` (Plan Phase 2.2, R36)
- [x] Confirm `uv.lock` is generated and committed (Plan Phase 2.2, R35, Rule #14)
- [x] Confirm no `requirements.txt` exists (Plan Phase 2.2, Rule #14)
- [x] Add `[tool.ruff]` line-length=100 (Plan Phase 2.3, R37, Rule #10)
- [x] Add `[tool.ruff.lint]` select `E,F,W,I,N,UP,B,C4,SIM`, ignore `E501` (Plan Phase 2.3, R37, Rule #10)
- [x] Add `[tool.coverage.run]` source=`src`, omit `src/main.py` (Plan Phase 2.3, R38, Rule #9)
- [x] Add `[tool.coverage.report]` `fail_under = 85` (Plan Phase 2.3, R38, Rule #9)
- [x] Create directory skeleton `src/ytdl/{shared,infra,services,sdk,cli}` with `__init__.py` (Plan Phase 2.4, R23)
- [x] Create `tests/unit/{shared,infra,services,sdk,cli}` skeleton (Plan Phase 2.4, R39)
- [x] Create `src/ytdl/shared/version.py` → `__version__ = "1.00"` (Plan Phase 2.4, R34, Rule #6)
- [x] Create `.gitignore` with `.env`, `cookies.txt`, `*.key`, `*.pem`, `downloads/` (Plan Phase 2.5, R33)
- [x] Phase 2 Gate — `uv sync` succeeds (Plan Gate 2 functional)
- [x] Phase 2 Gate — `uv run python -c "import ytdl"` works (Plan Gate 2 functional)
- [x] Phase 2 Gate — confirm `uv.lock` present, no `requirements.txt` (Plan Gate 2, Rule #14)
- [x] Phase 2 Gate — confirm `version.py` == `1.00` (Plan Gate 2, Rule #6)
- [x] Phase 2 Gate — run `uv run ruff check src/` zero violations (Plan Gate 2, Rule #10)
- [x] Phase 2 Gate — run uv-toolchain scan (no pip/python -m) (Plan Gate 2, Rule #14)
- [x] Phase 2 Gate — run file-size script, 0 files > 150 LOC (Plan Gate 2, Rule #8)
- [x] Phase 2 Commit — `chore(init): uv project, structure, versioning` (Rule #6, #14)

---

## Phase 3 — Configuration & Secrets
**Objective:** Externalize tunables; version+validate config; secret placeholders. | **Plan refs:** §6 | **Rules:** 4,6,7,11,12,13

- [x] RED: write failing test for `ConfigManager` loading a JSON file (Plan Phase 3.1, Rule #7)
- [x] RED: write failing test for `ConfigManager.get("a.b", default)` dotted lookup (Plan Phase 3.1, Rule #7)
- [x] RED: write failing test for `get` returning default on missing key (Plan Phase 3.1, R32, Rule #7)
- [x] RED: write failing test for version validation raising `ConfigVersionError` (Plan Phase 3.1, R34, Rule #7)
- [x] GREEN: implement `shared/config.py` `ConfigManager` JSON loader (Plan Phase 3.3, R32, Rule #8,#10)
- [x] GREEN: implement dotted `get(key, default)` (Plan Phase 3.3, R32)
- [x] GREEN: implement `SUPPORTED_CONFIG_VERSIONS = ["1.00"]` + `validate_config_version` (Plan Phase 3.3, R34, Rule #6)
- [x] GREEN: define `ConfigVersionError` exception (Plan Phase 3.3, R34)
- [x] REFACTOR: dedupe config-read logic; keep tests green (Plan Phase 3.3, Rule #2)
- [x] Create `config/setup.json` with `"version":"1.00"` (Plan Phase 3.2, R30, Rule #6)
- [x] Add `paths.output_dir` = `./downloads` to `setup.json` (Plan Phase 3.2, R30, R6req)
- [x] Add `defaults.resolution` = null to `setup.json` (Plan Phase 3.2, R30, R8req)
- [x] Add `defaults.sub_lang` = `en` to `setup.json` (Plan Phase 3.2, R30, R9req)
- [x] Add `defaults.modes` = `["video"]` to `setup.json` (Plan Phase 3.2, R30, R5req)
- [x] Add `audio.codec` = `mp3` and `audio.quality` = `192` to `setup.json` (Plan Phase 3.2, R30, R3req)
- [x] Add `subtitles.format` = `srt`, `subtitles.include_auto` = true to `setup.json` (Plan Phase 3.2, R30, R4req)
- [x] Add `ffmpeg.location` = `auto` to `setup.json` (Plan Phase 3.2, R30, R20)
- [x] Create `config/rate_limits.json` with `"version":"1.00"` (Plan Phase 3.2, R31, Rule #6)
- [x] Add `rate_limits.services.youtube` block (rpm, concurrent_max, burst, retry, max_retries) (Plan §6.2, R31, Rule #4)
- [x] Add `rate_limits.default` block (Plan §6.2, R31, Rule #4)
- [x] Add `queue` block (max_depth, drain_interval_seconds, timeout_seconds, overflow_strategy) (Plan §6.2, R31, Rule #5)
- [x] Document Fathom keys as N/A in config comment/README note (Plan §6.2, Rule #4)
- [x] Implement `constants.py` supported extensions (Plan Phase 3.4, R32, Rule #11)
- [x] Implement `constants.py` mode names + outtmpl/format templates (Plan Phase 3.4, R32, Rule #11)
- [x] Create `.env-example` with `YTDL_PROXY=` (Plan Phase 3.5, R33, Rule #13)
- [x] Add `YTDL_COOKIES_FILE=` to `.env-example` (Plan Phase 3.5, R33, Rule #13)
- [x] Verify rate limits are read from config not code (Plan Gate 3, Rule #4,#11)
- [x] Phase 3 Gate — configs load; version mismatch rejected; defaults returned (Plan Gate 3 functional)
- [x] Phase 3 Gate — confirm no hardcoded tunables in source (Plan Gate 3, Rule #11)
- [x] Phase 3 Gate — confirm config hierarchy present (Plan Gate 3, Rule #12)
- [x] Phase 3 Gate — confirm `.env-example` present, no secret literals (Plan Gate 3, Rule #13)
- [x] Phase 3 Gate — confirm both configs carry `"version":"1.00"` (Plan Gate 3, Rule #6)
- [x] Phase 3 Gate — run `uv run pytest tests/unit/shared/test_config.py` (Plan Gate 3 automated)
- [x] Phase 3 Gate — run secret-scan script (Plan Gate 3, Rule #13)
- [x] Phase 3 Gate — run ruff + file-size + coverage checks (Plan Gate 3, Rule #8,#9,#10)
- [x] Phase 3 Commit — `feat(config): versioned config, constants, env-example` (Rule #6)

---

## Phase 4 — Architecture & Shared Infrastructure
**Objective:** Gatekeeper / rate limiter / queue + yt-dlp/ffmpeg infra. | **Plan refs:** §4.1,§5,§6.2 | **Rules:** 1,2,3,5,7,8,10

- [x] RED: failing test for `RateLimiter` allows N requests/min then blocks (Plan Phase 4.1, Rule #7)
- [x] RED: failing test for `RateLimiter` reads limits from config (Plan Phase 4.1, R27, Rule #7)
- [x] RED: failing test for `RateLimiter` burst window behavior (Plan Phase 4.1, Rule #7)
- [x] GREEN: implement `shared/rate_limit.py` `RateLimiter` (sliding-window/token-bucket) (Plan Phase 4.1, R27, Rule #8,#10)
- [x] REFACTOR: extract window math helper; tests green (Plan Phase 4.1, Rule #2,#8)
- [x] RED: failing test for `DownloadQueue` FIFO ordering (Plan Phase 4.2, Rule #7)
- [x] RED: failing test for `DownloadQueue` max_depth overflow (queued, not crash) (Plan Phase 4.2, R28, Rule #7)
- [x] RED: failing test for `DownloadQueue` overflow_strategy `reject_oldest` (Plan Phase 4.2, R28, Rule #7)
- [x] RED: failing test for `DownloadQueue` drain (Plan Phase 4.2, Rule #7)
- [x] GREEN: implement `shared/queue.py` `DownloadQueue` FIFO + max_depth + drain + strategy (Plan Phase 4.2, R28, Rule #5,#8)
- [x] REFACTOR: simplify queue state; tests green (Plan Phase 4.2, Rule #2,#8)
- [x] RED: failing test for `ApiGatekeeper.execute` rate-check before call (Plan Phase 4.3, Rule #7)
- [x] RED: failing test for `ApiGatekeeper` retry/backoff on transient error (Plan Phase 4.3, R26, Rule #7)
- [x] RED: failing test for `ApiGatekeeper` max_retries exhaustion raises (Plan Phase 4.3, Rule #7)
- [x] RED: failing test for `ApiGatekeeper` logs each call (Plan Phase 4.3, Rule #7)
- [x] RED: failing test for `ApiGatekeeper` overflow enqueues to `DownloadQueue` (Plan Phase 4.3, R28, Rule #7)
- [x] GREEN: implement `shared/gatekeeper.py` `ApiGatekeeper.execute(callable, ...)` (Plan Phase 4.3, R26, Rule #3,#8)
- [x] GREEN: wire gatekeeper to `RateLimiter`, retry, logging, queue (Plan Phase 4.3, Rule #3,#5)
- [x] REFACTOR: extract retry/backoff helper; tests green (Plan Phase 4.3, Rule #2,#8)
- [x] RED: failing test for `FfmpegLocator.exe_dir()` returns dir of ffmpeg exe (Plan Phase 4.4, Rule #7)
- [x] GREEN: implement `infra/ffmpeg.py` `FfmpegLocator` wrapping `imageio_ffmpeg.get_ffmpeg_exe()` (Plan Phase 4.4, R20, Rule #8)
- [x] REFACTOR: cache located ffmpeg path; tests green (Plan Phase 4.4, Rule #2)
- [x] RED: failing test for `ytdlp_client` routes `extract_info` via gatekeeper (Plan Phase 4.5, R26, Rule #7)
- [x] RED: failing test for `ytdlp_client` routes `download` via gatekeeper (Plan Phase 4.5, R26, Rule #7)
- [x] GREEN: implement `infra/ytdlp_client.py` thin `yt_dlp.YoutubeDL` wrapper (Plan Phase 4.5, R19, Rule #8)
- [x] GREEN: ensure all net calls go through `ApiGatekeeper` (Plan Phase 4.5, R26, Rule #3)
- [x] REFACTOR: dedupe option-dict construction; tests green (Plan Phase 4.5, Rule #2)
- [x] RED: failing test for `BaseDownloader` builds shared ydl-opts/outtmpl (Plan Phase 4.6, Rule #7)
- [x] RED: failing test for `BaseDownloader` wires `ffmpeg_location` (Plan Phase 4.6, R20, Rule #7)
- [x] GREEN: implement `services/base.py` `BaseDownloader` shared opts builder (Plan Phase 4.6, R25, Rule #2,#8)
- [x] REFACTOR: ensure subclasses override only specifics; tests green (Plan Phase 4.6, Rule #2)
- [x] RED: failing test that opts builder injects `proxy` from `YTDL_PROXY` env, omitted when unset (PRD §6.4, Plan Phase 4.7, R44, Rule #7)
- [x] RED: failing test that opts builder injects `cookiefile` from `YTDL_COOKIES_FILE` env, omitted when unset (PRD §6.4, Plan Phase 4.7, R44, Rule #7)
- [x] GREEN: implement env-driven `proxy`/`cookiefile` injection in opts builder (PRD §6.4, Plan Phase 4.7, R44, Rule #8,#11)
- [x] Phase 4 Gate — proxy/cookies consumed only from env when set, omitted when unset (Plan Gate 4 functional, R44, PRD §6.4)
- [x] Phase 4 Gate — rate limit enforced; overflow queued not crashed (Plan Gate 4 functional)
- [x] Phase 4 Gate — retries on transient error verified (Plan Gate 4 functional)
- [x] Phase 4 Gate — grep: no direct `YoutubeDL(`/`requests.` outside `infra/` (Plan Gate 4, Rule #1,#3)
- [x] Phase 4 Gate — confirm `BaseDownloader` removes duplication (Plan Gate 4, Rule #2)
- [x] Phase 4 Gate — run `uv run pytest tests/unit/shared tests/unit/infra` (Plan Gate 4 automated)
- [x] Phase 4 Gate — run ruff + file-size + coverage checks (Plan Gate 4, Rule #8,#9,#10)
- [x] Phase 4 Commit — `feat(infra): gatekeeper, rate limiter, queue, ffmpeg, base downloader` (Rule #6)

---

## Phase 5 — Domain Implementation (Video / Audio / Subtitles / Metadata)
**Objective:** Three downloader services + metadata, each subclassing `BaseDownloader`. | **Plan refs:** §3.2,§5 | **Rules:** 2,7,8,10

- [x] RED: failing test for `MetadataService` resolves info dict / title (Plan Phase 5.1, Rule #7)
- [x] GREEN: implement `services/metadata.py` info/title extraction (Plan Phase 5.1, R12, Rule #8)
- [x] REFACTOR: trim metadata mapping; tests green (Plan Phase 5.1, Rule #2)
- [x] RED: failing test for `VideoDownloader` builds `bv*[height<=RES]+ba/b` (Plan Phase 5.2, R2, Rule #7)
- [x] RED: failing test for `VideoDownloader` sets `merge_output_format="mp4"` (Plan Phase 5.2, R2, Rule #7)
- [x] RED: failing test for `VideoDownloader` no-resolution → best (`bv*+ba/b`) (Plan Phase 5.2, R8, Rule #7)
- [x] GREEN: implement `services/video.py` `VideoDownloader` (Plan Phase 5.2, R2, Rule #8)
- [x] REFACTOR: clean format-string builder; tests green (Plan Phase 5.2, Rule #2)
- [x] RED: failing test for `AudioDownloader` adds `FFmpegExtractAudio` postprocessor (Plan Phase 5.3, R3, Rule #7)
- [x] RED: failing test for `AudioDownloader` codec/quality read from config (Plan Phase 5.3, R3, Rule #11)
- [x] GREEN: implement `services/audio.py` `AudioDownloader` (Plan Phase 5.3, R3, Rule #8)
- [x] REFACTOR: dedupe postprocessor list builder; tests green (Plan Phase 5.3, Rule #2)
- [x] RED: failing test for `SubtitleDownloader` sets writesubtitles+writeautomaticsub (Plan Phase 5.4, R4, Rule #7)
- [x] RED: failing test for `SubtitleDownloader` `subtitleslangs=[lang]` (Plan Phase 5.4, R9, Rule #7)
- [x] RED: failing test for `SubtitleDownloader` `FFmpegSubtitlesConvertor` → srt (Plan Phase 5.4, R11, Rule #7)
- [x] RED: failing test for subtitle output named `<name>.<lang>.srt` (Plan Phase 5.4, R11, Rule #7)
- [x] RED: failing test for auto-only-captions fallback path (Plan §3 R2 risk, Rule #7)
- [x] GREEN: implement `services/subtitles.py` `SubtitleDownloader` (Plan Phase 5.4, R4, Rule #8)
- [x] REFACTOR: share subtitle opts via base; tests green (Plan Phase 5.4, Rule #2)
- [x] Write docstrings for all four service classes (Plan §4, Rule #1)
- [x] Phase 5 Gate — each service builds correct ydl-opts (mocked) (Plan Gate 5 functional)
- [x] Phase 5 Gate — subtitle convertor guarantees `.srt`; manual+auto covered (Plan Gate 5 functional)
- [x] Phase 5 Gate — confirm subclasses override only specifics, no dup opts (Plan Gate 5, Rule #2)
- [x] Phase 5 Gate — run `uv run pytest tests/unit/services` (Plan Gate 5 automated)
- [x] Phase 5 Gate — run ruff + file-size + coverage checks (Plan Gate 5, Rule #8,#9,#10)
- [x] Phase 5 Commit — `feat(services): video, audio, subtitle, metadata downloaders` (Rule #6)

---

## Phase 6 — SDK / API Surface
**Objective:** Expose every op via `YoutubeDownloaderSDK`; fetch-once for combined modes. | **Plan refs:** §4.1,§5 | **Rules:** 1,2,7

- [x] RED: failing test for `YoutubeDownloaderSDK.download(...)` signature/params (Plan Phase 6.1, R24, Rule #7)
- [x] RED: failing test for per-mode SDK methods (video/audio/subs) (Plan Phase 6.1, R24, Rule #7)
- [x] RED: failing test that combined modes resolve info once (Plan Phase 6.2, R12, Rule #7)
- [x] RED: failing test that combined modes build union of postprocessors (Plan Phase 6.2, R12, Rule #7)
- [x] RED: failing test that no output flags → defaults to video (Plan Phase 6.2, R5, Rule #7)
- [x] GREEN: implement `sdk/sdk.py` `YoutubeDownloaderSDK` (Plan Phase 6.1, R24, Rule #1,#8)
- [x] GREEN: implement combinability (resolve once + union PP) (Plan Phase 6.2, R5,R12)
- [x] GREEN: ensure SDK is only externally-imported object (Plan Phase 6.3, R24, Rule #1)
- [x] REFACTOR: dedupe SDK→service wiring; tests green (Plan Phase 6, Rule #2)
- [x] Write docstrings for every public SDK method (Plan §4, Rule #1)
- [x] Phase 6 Gate — combined `--video --audio --subs` = single resolve + union PP (Plan Gate 6 functional)
- [x] Phase 6 Gate — default-video honored when no flags (Plan Gate 6 functional)
- [x] Phase 6 Gate — all ops reachable via SDK without importing internals (Plan Gate 6, Rule #1)
- [x] Phase 6 Gate — run `uv run pytest tests/unit/sdk` (Plan Gate 6 automated)
- [x] Phase 6 Gate — run ruff + file-size + coverage checks (Plan Gate 6, Rule #8,#9,#10)
- [x] Phase 6 Commit — `feat(sdk): single-entry SDK with fetch-once combinability` (Rule #1,#6)

---

## Phase 7 — CLI / External Interface
**Objective:** argparse CLI delegating 100% to SDK + behavioral reqs. | **Plan refs:** §3.1,§3.3 | **Rules:** 1,7,8,10

- [x] RED: failing test for positional `url` parsing (Plan Phase 7.1, R1, Rule #7)
- [x] RED: failing test for `--video/--audio/--subs` flag parsing (Plan Phase 7.1, R2,R3,R4, Rule #7)
- [x] RED: failing test for `-o/--output-dir` parsing (Plan Phase 7.1, R6, Rule #7)
- [x] RED: failing test for `-n/--name` parsing + default `%(title)s` (Plan Phase 7.1, R7, Rule #7)
- [x] RED: failing test for `--resolution` parsing (Plan Phase 7.1, R8, Rule #7)
- [x] RED: failing test for `--sub-lang` parsing + default `en` (Plan Phase 7.1, R9, Rule #7)
- [x] RED: failing test for `--version` prints code+config version (Plan Phase 7.1, R10, Rule #7)
- [x] RED: failing test that no output flag → defaults to video (Plan Phase 7.2, R5, Rule #7)
- [x] RED: failing test that combinable toggles pass through to SDK (Plan Phase 7.2, R5, Rule #7)
- [x] RED: failing test for UTF-8 stdout reconfiguration (Plan Phase 7.3, R13, Rule #7)
- [x] RED: failing test for structured progress logging per phase (Plan Phase 7.3, R14, Rule #7)
- [x] RED: failing test for idempotent output-dir creation (Plan Phase 7.4, R16, Rule #7)
- [x] RED: failing test for deterministic exit codes (success/bad-url/version-mismatch) (Plan Phase 7.4, R15, Rule #7)
- [x] RED: failing test for non-zero exit on network failure after retries (PRD §3.3, Plan Phase 7.4, R15, Rule #7)
- [x] RED: failing test for non-zero exit on unsupported request (PRD §3.3, Plan Phase 7.4, R15, Rule #7)
- [x] RED: failing test that CLI is non-interactive (no prompts) (Plan Phase 7.4, R17, Rule #7)
- [x] GREEN: implement `cli/main.py` argparse with all flags (Plan Phase 7.1, R1,R6-R10, Rule #8)
- [x] GREEN: implement default-to-video + combinable toggles (Plan Phase 7.2, R5)
- [x] GREEN: implement UTF-8 stdout reconfig (Plan Phase 7.3, R13)
- [x] GREEN: implement structured progress logging (Plan Phase 7.3, R14)
- [x] GREEN: implement idempotent dir creation (Plan Phase 7.4, R16)
- [x] GREEN: implement deterministic exit codes for all four conditions — invalid URL, network-failure-after-retries, unsupported request, config-version mismatch (PRD §3.3, Plan Phase 7.4, R15)
- [x] GREEN: ensure CLI delegates 100% to SDK (no business logic) (Plan Phase 7, R24, Rule #1)
- [x] GREEN: implement `src/main.py` shim for `python -m ytdl` (Plan Phase 7.5, A2)
- [x] REFACTOR: extract arg→SDK mapping helper; tests green (Plan Phase 7, Rule #2)
- [x] Write `--help` text and docstrings for CLI (Plan §3.1, Rule #1)
- [x] Phase 7 Gate — all flags parse; `--version` prints versions (Plan Gate 7 functional)
- [x] Phase 7 Gate — missing dir auto-created; non-zero exit on bad URL/version (Plan Gate 7 functional)
- [x] Phase 7 Gate — confirm zero business logic in CLI (delegates to SDK) (Plan Gate 7, Rule #1)
- [x] Phase 7 Gate — run `uv run pytest tests/unit/cli` (Plan Gate 7 automated)
- [x] Phase 7 Gate — run ruff + file-size + coverage checks (Plan Gate 7, Rule #8,#9,#10)
- [x] Phase 7 Commit — `feat(cli): argparse interface delegating to SDK` (Rule #1,#6)

---

## Phase 8 — Testing & Coverage
**Objective:** Prove ≥85% coverage with all boundaries mocked. | **Plan refs:** §8 | **Rules:** 7,9

- [x] Implement `tests/conftest.py` `mock_ytdl` fixture (Plan Phase 8.1, R39, Rule #7)
- [x] Implement `conftest.py` mock `imageio_ffmpeg`/`subprocess` fixtures (Plan Phase 8.1, R39, Rule #7)
- [x] Implement `conftest.py` `sample_config` fixture (Plan Phase 8.1, R39)
- [x] Implement `conftest.py` `tmp_output_dir` fixture (Plan Phase 8.1, R39)
- [x] Add error-path test: invalid URL (Plan Phase 8.2, R39, Rule #7)
- [x] Add error-path test: empty/`None` args (Plan Phase 8.2, R39, Rule #7)
- [x] Add error-path test: rate-limit overflow → queued (Plan Phase 8.2, R28, Rule #7)
- [x] Add error-path test: config-version mismatch (Plan Phase 8.2, R34, Rule #7)
- [x] Confirm no network and no real ffmpeg invoked in unit tests (Plan Gate 8 functional, R39)
- [x] Run coverage; raise gaps to ≥85% (Plan Phase 8.3, R38, Rule #9)
- [x] Confirm test files also ≤150 LOC (Plan Phase 8.3, Rule #8)
- [x] Phase 8 Gate — full suite green (Plan Gate 8 functional)
- [x] Phase 8 Gate — coverage ≥85% enforced by `fail_under` (Plan Gate 8, Rule #9)
- [x] Phase 8 Gate — confirm happy+error per public method (Plan Gate 8, Rule #7)
- [x] Phase 8 Gate — run `uv run pytest tests/ --cov=src --cov-report=term-missing` (Plan Gate 8 automated)
- [x] Phase 8 Gate — run ruff + file-size checks (Plan Gate 8, Rule #8,#10)
- [x] Phase 8 Commit — `test: fixtures, error paths, coverage >=85%` (Rule #6,#9)

---

## Phase 9 — Security Review
**Objective:** No secrets in source; secret hygiene complete. | **Plan refs:** §6.4 | **Rules:** 13

- [x] Run secret-scan over `src/` (Plan Phase 9.1, Rule #13)
- [x] Confirm no API keys/tokens/passwords in source (Plan Phase 9.1, R33, Rule #13)
- [x] Confirm `.env`, `cookies.txt`, `*.key`, `*.pem` git-ignored (Plan Phase 9.2, R33)
- [x] Confirm `.env-example` committed with placeholders only (Plan Phase 9.2, R33, Rule #13)
- [x] Verify optional proxy/cookies read from env, never hardcoded (Plan Gate 9 functional, R32)
- [x] Phase 9 Gate — secret scan clean (Plan Gate 9, Rule #13)
- [x] Phase 9 Gate — `.env-example` present (Plan Gate 9, Rule #13)
- [x] Phase 9 Gate — run secret-scan script + `.gitignore` check (Plan Gate 9 automated)
- [x] Phase 9 Commit — `chore(security): secret scan + env hygiene verified` (Rule #6,#13)

---

## Phase 10 — Documentation & Deliverables
**Objective:** README + authoritative PRD/PLAN + future scope. | **Plan refs:** §4 tree,§11 | **Rules:** 14

- [x] Write `README.md` install section (`uv sync`) (Plan Phase 10.1, R41, Rule #14)
- [x] Write `README.md` PowerShell usage examples (Plan Phase 10.1, R41)
- [x] Write `README.md` flags table (Plan Phase 10.1, R41)
- [x] Write `README.md` config overview (Plan Phase 10.1, R41)
- [x] Confirm `docs/PRD.md` present and authoritative (Plan Phase 10.2, R41)
- [x] Confirm `docs/PLAN.md` present and authoritative (Plan Phase 10.2, R41)
- [x] Document future GPU/transcription pattern (cuda_libs in place, never copied) (Plan Phase 10.2, R43)
- [x] Document future D: drive-safety guard for graph re-consult (Plan §3 R4 risk, R22)
- [x] Phase 10 Gate — README commands run as written (Plan Gate 10 functional)
- [x] Phase 10 Gate — docs reference uv-only commands (Plan Gate 10, Rule #14)
- [x] Phase 10 Commit — `docs: README, future scope, drive-safety note` (Rule #6)

---

## Phase 11 — Release & Verification (final gate)
**Objective:** Prove S1–S3 and full quality compliance end-to-end. | **Plan refs:** §1.3,§10 | **Rules:** all 14

- [x] Run `uv sync` (Plan Phase 11.1, R42)
- [x] Run `uv run ruff check src/ tests/` zero violations (Plan Phase 11.1, Rule #10)
- [x] Run `uv run pytest tests/ --cov=src --cov-report=term-missing` (Plan Phase 11.1, Rule #9, R42)
- [x] Run file-size script, 0 files > 150 LOC (Plan Phase 11.1, Rule #8)
- [x] Run secret-scan script clean (Plan Phase 11.1, Rule #13)
- [x] Manual smoke test: `uv run python -m ytdl "<URL>" --video --audio --subs -o .\downloads -n sample --resolution 720` (Plan Phase 11.2, R18, S1)
- [x] Verify `sample.mp4` produced and plays (Plan Phase 11.2, R2, S1)
- [x] Verify `sample.mp3` produced and plays (Plan Phase 11.2, R3, S1)
- [x] Verify `sample.en.srt` produced and opens (Plan Phase 11.2, R4, S1)
- [x] Confirm no system FFmpeg / no GPU needed (Plan Phase 11.2, R18, S2)
- [x] Confirm non-goals respected: no GUI/web (Plan Phase 11.3, R40)
- [x] Confirm non-goals respected: no playlist CLI (Plan Phase 11.3, R40)
- [x] Confirm non-goals respected: no DRM bypass (Plan Phase 11.3, R40)
- [x] Complete Sign-Off: 100% PRD coverage (Plan §11 sign-off, S3)
- [x] Complete Sign-Off: 14/14 rules PASS (Plan §10, S3)
- [x] Complete Sign-Off: no open questions (Plan §8)
- [x] Phase 11 Gate — S1–S3 met; smoke artifacts valid (Plan Gate 11 functional)
- [x] Phase 11 Commit — `chore(release): v1.00 verification + sign-off` (Rule #6)

---

## Plan Coverage Map
| Plan Element | Type | Satisfying TODO line(s) | Status |
|---|---|---|---|
| Phase 1 (Discovery) | Phase | Phase 1 block | PASS |
| Phase 2 (Init) | Phase | Phase 2 block | PASS |
| Phase 3 (Config) | Phase | Phase 3 block | PASS |
| Phase 4 (Infra) | Phase | Phase 4 block | PASS |
| Phase 5 (Domain) | Phase | Phase 5 block | PASS |
| Phase 6 (SDK) | Phase | Phase 6 block | PASS |
| Phase 7 (CLI) | Phase | Phase 7 block | PASS |
| Phase 8 (Testing) | Phase | Phase 8 block | PASS |
| Phase 9 (Security) | Phase | Phase 9 block | PASS |
| Phase 10 (Docs) | Phase | Phase 10 block | PASS |
| Phase 11 (Release) | Phase | Phase 11 block | PASS |
| R1–R12 (Func) | PRD Coverage | Phases 5,6,7 RED/GREEN tasks | PASS |
| R13–R17 (NFR/behavioral) | PRD Coverage | Phase 7 tasks | PASS |
| R18 (PowerShell/no-ffmpeg/no-GPU) | Constraint | Phase 11 smoke tasks | PASS |
| R19 (yt-dlp) | Constraint | Phase 4.5 tasks | PASS |
| R20 (imageio-ffmpeg) | Constraint | Phase 4.4 tasks | PASS |
| R21 (no GPU) | Constraint | Phase 1 confirm task | PASS |
| R22 (D: drive-safety) | Risk | Phase 10 doc task | PASS |
| R23 (src layout) | Arch | Phase 2.4 tasks | PASS |
| R24 (SDK single entry) | Arch/Rule 1 | Phase 6 + Phase 7 delegation | PASS |
| R25 (BaseDownloader no-dup) | Arch/Rule 2 | Phase 4.6 tasks | PASS |
| R26 (gatekeeper) | Arch/Rule 3 | Phase 4.3/4.5 tasks | PASS |
| R27 (rate limiter) | Arch/Rule 4 | Phase 4.1 + Phase 3 config | PASS |
| R28 (queue) | Arch/Rule 5 | Phase 4.2 tasks | PASS |
| R29 (≤150 LOC) | Arch/Rule 8 | every phase gate file-size task | PASS |
| R30 (setup.json) | Config | Phase 3 setup.json tasks | PASS |
| R31 (rate_limits.json) | Config | Phase 3 rate_limits tasks | PASS |
| R32 (no hardcoded) | Config/Rule 11 | Phase 3 constants + verify task | PASS |
| R33 (.env-example/gitignore) | Security/Rule 13 | Phase 3 + Phase 9 tasks | PASS |
| R34 (version+validation) | Config/Rule 6 | Phase 2.4 + Phase 3.3 tasks | PASS |
| R35 (uv/lock/py3.10) | Tool/Rule 14 | Phase 2.1/2.2 tasks | PASS |
| R36 (deps) | Tool | Phase 2.2 tasks | PASS |
| R37 (ruff config) | Quality/Rule 10 | Phase 2.3 + every gate | PASS |
| R38 (coverage 85) | Quality/Rule 9 | Phase 2.3 + Phase 8 | PASS |
| R39 (TDD/mocks/fixtures) | Test/Rule 7 | Phase 8 + RED tasks everywhere | PASS |
| R40 (non-goals) | Constraint | Phase 11.3 tasks | PASS |
| R41 (PRD in docs) | Deliverable | Phase 10.2 tasks | PASS |
| R42 (verification cmds) | Deliverable | Phase 11.1 tasks | PASS |
| R43 (future scope incl cuda_libs) | Deliverable | Phase 10.2 task | PASS |
| R44 (consume YTDL_PROXY/YTDL_COOKIES_FILE from env) | Func/NFR | Phase 4.7 RED/GREEN + gate tasks | PASS |
| Sign-Off: 100% PRD coverage | Sign-Off | Phase 11 sign-off task | PASS |
| Sign-Off: 14/14 rules | Sign-Off | Phase 11 sign-off task | PASS |
| Sign-Off: no open questions | Sign-Off | Phase 11 sign-off task | PASS |
| Sign-Off: phase gates defined | Sign-Off | gate tasks in every phase | PASS |

---

## Quality Rules Coverage (audit)
| Rule # | Where enforced in TODO | Verification task line |
|---|---|---|
| 1 SDK Architecture | Phases 4,6,7 | "grep: no direct YoutubeDL outside infra" / "CLI delegates 100% to SDK" |
| 2 OO Design | every impl phase | each REFACTOR task + "BaseDownloader removes duplication" |
| 3 API Gatekeeper | Phase 4 | "implement ApiGatekeeper.execute" + gate grep |
| 4 Rate Limit Config | Phases 3,4 | "RateLimiter reads limits from config" |
| 5 Queue Mgmt | Phase 4 | "DownloadQueue max_depth overflow (queued)" |
| 6 Version Control | Phase 2 + every commit | "version.py == 1.00" + commit tasks |
| 7 TDD | every phase | all RED tasks |
| 8 File Size ≤150 | every phase gate | "file-size script 0 files > 150 LOC" |
| 9 Coverage ≥85% | Phases 2,8,11 | "coverage ≥85% fail_under" |
| 10 Linter | every phase gate | "uv run ruff check zero violations" |
| 11 No Hardcoded | Phases 3,9 | "no hardcoded tunables" + "codec/quality from config" |
| 12 Config Architecture | Phase 3 | "config hierarchy present" |
| 13 Secrets Mgmt | Phases 3,9 | ".env-example present" + "secret scan clean" |
| 14 uv Toolchain | Phases 2,10,11 | "uv.lock present, no requirements.txt" |

---

## Self-Review (Gap Analysis)
**Method:** walked every Phase (1–11), every Phase Gate criterion, every PRD-Coverage row (R1–R43), every Quality-Rule row (1–14), every Sign-Off row, and every Risk/Deliverable. For each, located the satisfying TODO line(s) and confirmed presence.

Self-review gaps found and patched in-place (GA.1–GA.5):
- GA.1 — Auto-only-caption fallback (PRD §3 R2 risk) had no test → added RED task in Phase 5 (1 task)
- GA.2 — Fathom "N/A" documentation (Plan §6.2) was unmapped → added Phase 3 documentation task (1 task)
- GA.3 — `src/main.py` `-m ytdl` shim (A2) was implicit → added explicit Phase 7.5 GREEN task (1 task)
- GA.4 — D: drive-safety future note (Risk R4/R22) was unmapped → added Phase 10 doc task (1 task)
- GA.5 — `--help`/docstrings (Rule 1 docs) thin → added explicit doc tasks in Phases 5,6,7 (3 tasks)
- GA.6 — (PRD audit) `YTDL_PROXY`/`YTDL_COOKIES_FILE` declared in `.env-example` but never consumed → added Phase 4.7 RED×2 + GREEN + gate (4 tasks); PLAN back-propagated (R44) (PRD §2 A1/§6.4)
- GA.7 — (PRD audit) exit-code contract only tested for 3 of 4 conditions → added RED×2 for network-failure-after-retries + unsupported-request and expanded GREEN (3 tasks); PLAN Phase 7 gate enumerated (PRD §3.3)

**Verification:** Plan Coverage Map traces every Plan element → TODO line; Quality Rules Coverage proves all 14 rules enforced; every phase ends with Gate + Commit tasks; every code task is preceded by a RED test task.

---

## Sign-Off
| Check | Status | Evidence |
|---|---|---|
| >= 200 atomic tasks | PASS | task count = 244 |
| 100% plan coverage | PASS | Plan Coverage Map |
| All quality rules cited | PASS | Quality Rules Coverage (14/14) |
| RED-before-GREEN ordering enforced | PASS | every GREEN preceded by RED in file order |
| Gate + Commit tasks present in every phase | PASS | Phases 1–11 each end with Gate + Commit |
| No untraceable tasks | PASS | every task carries a `(…)` citation |
| No remaining gaps after self-review | PASS | GA.1–GA.5 patched |
