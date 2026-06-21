# PRD — Mix-Video Pipeline (idea + song → one beat-synced mixed video)

| Field | Value |
|-------|-------|
| Project | `youtube-downloader` (movie pipeline) |
| Document version | 1.06 |
| Date | 2026-06-21 |
| Status | Implemented |
| Builds on | PRD-movie-agent, PRD-tracks, PRD-beatsync |

## 1. Goal
A **single, wizard-driven, resumable pipeline** that turns a one-line idea + a leading
song into a finished, **beat-synced mixed video** — and plays it. The agent does the
whole job: setup → understand the music → script it scene-by-scene → find + download the
best **real** YouTube footage per scene → build → render → play. No fake/generated video.

## 2. Architecture — Dr. Segal's Three-Layer Agent Architecture (Software → Skill → Agent)
* **Software (תוכנה)** — `services/pipeline/` orchestrator + the SDK. Deterministic
  stages with **file-on-disk state** (resume), adapted from GtaiGrader.
* **Skill (סקיל)** — `movie-script-writer` (authors the scene script),
  `video-content-matcher` (per-scene matching).
* **Agent (סוכן)** — `youtube-movie-maker`, the **Orchestrator Agent (סוכן מנהל)** that
  coordinates the wizard, the skills, and the `youtube-fetcher` **worker sub-agent**
  (Parallel Execution) — Segal's *QA Orchestrator Agent* pattern.

## 3. Pipeline stages (each persists to the BUILD folder → resumable)
```
WIZARD     config.json         leading song, output, scene target, sync target+mode, LLM vendor/auth
STRUCTURE  structure.json      analyze song → N scene slots sampled across the bars (--plan-movie)
SCRIPT     script.json         topic+vibe+structure → N {visual_description, search_query}
MATCH      scenarios/scn_<n>.json → segments.json   per-scene --search → best section (resumable)
FETCH      videos/seg_<n>.mp4  download unique URLs (dedup + resume)
BUILD      videos/movie.yaml   build_movie(leading, sync) — beat-synced playlist
RENDER     final mp4 + VLC     play_playlist; print location
REPORT     pipeline_report.md  stages, counts, output
```
No leading song → STRUCTURE makes fixed-length scenes and beat-sync is off (config
property `MovieConfig.stages`). Re-running any command **resumes** (skips done stages).

## 4. LLM auth (multi-vendor, default Claude CLI-login — adapted from basic-clis)
`services/llm/`: an `LlmProvider` ABC with two modes per vendor — **CLI login** (shell
out to the vendor CLI, e.g. `claude -p`, using the subscription) and **API key**. The
**default is Claude via CLI login**; in CLI mode the API-key env vars
(`ANTHROPIC_API_KEY`/`CLAUDECODE`/…) are **scrubbed from the child env** so the login is
used, not a key. Config-driven (`setup.json` `llm.*`); keys in `.env`. The agent path may
instead author `script.json` itself (no provider call).

## 5. Surface
* SDK (Rule 1): `make_movie(config)`, `run_movie_pipeline(path)`, `plan_movie(config)`,
  `movie_wizard(path)` (via `PipelineMixin`).
* CLI: `--movie-wizard` · `--plan-movie` · `--make-movie --config <file>` with
  `--scenes/--vendor/--auth/--leading` overrides; plus the bridges `--search … -o`,
  `--to-segments`, `--fetch-movie`, `--build-movie --sync`.

## 6. glb-quality compliance
SDK-first via `PipelineMixin`/`MovieMixin` mixins (1) · OOP + reuse of
`search`/`builder`/`AudioAnalyzer`/`beat_time`, provider ABC, no dup (2) · YouTube on the
rate-limited `YtDlpClient` gatekeeper (3-5) · config + code → **1.06**, playlists 1.05 (6)
· TDD, subprocess/urllib/ffmpeg/network mocked (7) · every file ≤150; split into
`pipeline/`, `llm/`, `cli/pipeline_run.py`, `sdk/mixins.py` (8) · ≥85% cov (9) · ruff
clean (10) · scene_target/targets/vendor/strip-keys from `setup.json` (11-12) ·
`.env-example` + env-scrub, no secrets (13) · uv (14).

## 7. Verification
`uv run ruff check` · `uv run pytest --cov=src` (≥85%) · file-size ≤150 · then:
`--movie-wizard -o config.json` (writes config) · `--plan-movie --config config.json`
(writes structure.json) · author/auto `script.json` · `--make-movie --config config.json`
(→ segments/videos/movie.yaml/final mp4 + VLC + report) · re-run resumes · default uses
Claude CLI-login (no key); `--auth api` + a key uses the API.

## 8. Out of scope (this iteration)
Sub-shot (frame-by-frame) scripting; auto-choosing multiple sections of one video per
scene (dup videos across scenes ARE supported); OpenAI/Gemini CLI-login + non-Claude API
mode (config hooks/stubs); parallel/threaded search drain (sequential, rate-limited,
resumable).
