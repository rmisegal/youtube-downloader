# PRD — YouTube Movie Maker (LLM agent + skills + project tools)

| Field | Value |
|-------|-------|
| Project | `youtube-downloader` (movie-agent extension) |
| Document version | 1.05 |
| Date | 2026-06-21 |
| Status | Implemented |
| Builds on | the SDK (download / playlist mixer), PRD-tracks, PRD-beatsync |

## 1. Goal
An **LLM agent that turns a one-line movie idea into a finished film** by orchestrating
skills + a sub-agent and using this project's editing tools. It scripts the idea into a
shot list, finds matching **real** YouTube footage, downloads it, and **edits it
together into one video** — it never generates/fakes footage.

## 2. Components
* **Skill `video-content-matcher`** (`.claude/skills/`) — given ordered topics (+ min
  durations), search YouTube + the web, validate durations (fallback loop), and emit the
  strict JSON segment array (the user-supplied schema).
* **Agent skill `youtube-movie-maker`** (`.claude/skills/`) — the orchestrator: idea →
  shot script → matcher skill → fetcher sub-agent → `--build-movie` → `--playlist-file`.
* **Sub-agent `youtube-fetcher`** (`.claude/agents/`) — downloads each segment's
  `video_url` to `seg_<sequence_number>.mp4` via the rate-limited downloader.
* **Project tools (the agent's hands), exposed via the SDK (Rule 1):**
  * `SDK.search(query, results)` → `--search "<q>" --results N` — candidate videos +
    durations (yt-dlp `ytsearch`, through the rate-limited `YtDlpClient`).
  * `SDK.build_movie(segments_json, video_dir, leading_audio, out_path)` →
    `--build-movie <json> --dir <videos>` — segments JSON → playlist YAML.
  * existing `SDK.download(...)` and `SDK.play_playlist(...)` → `--video`, `--playlist-file`.

## 3. Pipeline
```
idea ─► (1) shot script (topics + min durations)
     ─► (2) video-content-matcher skill ─► BUILD/segments.json
     ─► (3) youtube-fetcher sub-agent  ─► BUILD/videos/seg_<n>.mp4
     ─► (4) --build-movie              ─► BUILD/videos/movie.yaml
     ─► (5) --playlist-file            ─► one film (VLC + saved file)
```
The builder makes one ordered video member per scene playing its exact `start_time`
in-point for `duration_seconds`; clips keep their own audio, or `--leading` adds a music
score. The `movie.yaml` can be enriched with title/subtitle **tracks** or **beat-sync**.

## 4. Code (new, glb-quality compliant)
`services/movie/search.py` (`search_youtube`) · `services/movie/builder.py`
(`build_movie_playlist`, `to_seconds`, `load_segments`) · `sdk/movie_mixin.py`
(`MovieMixin` mixed into `YoutubeDownloaderSDK`) · `cli/movie_run.py`
(`run_search`/`run_build_movie`) · `cli/argdefs.py` (`--search`/`--results`/
`--build-movie`/`--leading`/`--produce`).

## 5. glb-quality compliance
| # | Rule | How |
|---|------|-----|
| 1 | SDK entry point | `search`/`build_movie` on the SDK (via `MovieMixin`); CLI delegates |
| 2 | OOP / no dup | mixin; pure helper functions reused; no duplication |
| 3 | API gatekeeper | `search` uses the rate-limited `YtDlpClient` (no raw yt-dlp) |
| 4–5 | Rate limits / queue | inherited from the existing gatekeeper + `rate_limits.json` |
| 6 | Versioning | playlist `1.05`; config/code `1.05` |
| 7 | TDD | `tests/unit/services/movie/test_movie.py` (search map, HH:MM:SS, builder, validation) |
| 8 | ≤150 lines | handlers split into `movie_run.py`; SDK methods in a mixin file |
| 9 | ≥85% coverage | maintained (~93%) |
| 10 | Ruff | zero violations |
| 11 | No hardcoded | folders/leading from args; naming convention `seg_<n>.mp4` documented |
| 12 | Config arch | reuses `setup.json`/`rate_limits.json` |
| 13 | Secrets | none added; `.env-example` present |
| 14 | uv | `uv add`, `uv run` throughout; skills/agent call `uv run python -m ytdl` |

## 6. Verification
`uv run ruff check` · `uv run pytest --cov=src` (≥85%) · file-size ≤150 ·
`uv run python -m ytdl --search "city timelapse" --results 5` (JSON of candidates) ·
`uv run python -m ytdl --build-movie segments.json --dir videos` (writes `movie.yaml`) ·
end-to-end: run the `youtube-movie-maker` skill on an idea → segments → download → film.

## 7. Out of scope
AI-generated/fake footage; precise sub-second transcript alignment (matcher uses
chapters/transcripts/metadata to estimate start times); automatic music selection.
