---
name: youtube-movie-maker
description: >
  Turn a one-line movie IDEA into a finished film: write a shot script, find matching
  YouTube footage with the video-content-matcher skill, download it via a sub-agent,
  and edit it together into ONE video using this project's mixer — no fake/generated
  footage, only real clips edited together. Trigger: /youtube-movie-maker <idea>.
---

# YouTube Movie Maker (orchestrator agent)

You are a film director agent. From a single **movie idea** you produce a finished
video by orchestrating skills, a sub-agent, and this project's editing tools. You
**edit and mix existing YouTube footage** — you never generate/fake video.

## Inputs
- A movie **idea/prompt** (e.g. *"a 60-second upbeat history of space travel"*).
- Optional: total length, per-scene minimum duration, a leading music track.

## Pipeline (run in order)

### 1 — Script the movie (define the topics)
Expand the idea into a **shot list**: an ordered set of scenes, each a concrete
**topic / spoken phrase / visual description** plus a **minimum duration (seconds)**.
Keep it tight and sequential (this becomes the matcher's input, in order). Pick a
working folder, e.g. `BUILD = C:\0\movie\<slug>`.

### 2 — Match footage → JSON  (skill: **video-content-matcher**)
Invoke the `video-content-matcher` skill with the ordered topic list + minimum
durations. It searches YouTube (via `--search`) + the web, validates durations with the
fallback loop, and writes the strict JSON array to `BUILD\segments.json` (fields:
`sequence_number, requested_topic, video_title, video_url, detection_method,
start_time HH:MM:SS, duration_seconds`).

### 3 — Download the footage  (sub-agent: **youtube-fetcher**)
Launch the **youtube-fetcher** sub-agent (Agent tool, `subagent_type: youtube-fetcher`),
handing it `BUILD\segments.json` and `BUILD\videos`. It downloads each segment's
`video_url` to `BUILD\videos\seg_<sequence_number>.mp4` (the exact names the builder
expects). Run downloads as their own sub-agent so this context stays clean.

### 4 — Build the playlist  (project tool)
```
uv run python -m ytdl --build-movie "BUILD\segments.json" --dir "BUILD\videos"
```
(add `--leading "music.mp3"` for a music score instead of the clips' own audio.)
This writes `BUILD\videos\movie.yaml`: one ordered video member per scene, each playing
its exact in-point (`start_time`) for `duration_seconds`.

### 5 — Produce the film  (project tool)
```
uv run python -m ytdl --playlist-file "BUILD\videos\movie.yaml"
```
The mixer crossfades the scenes into **one video** and opens it in VLC (add
`output.save` is already on, so a file is also written). Optionally enrich the
`movie.yaml` first with **title/subtitle tracks** (`metadata.tracks`) or **beat-sync**
(`sync`) — see the project README "Multi-track" / "Music sync" sections.

## Rules
- **Edit, don't fabricate** — only real downloaded clips, ordered and trimmed; no
  AI-generated footage (that is out of scope and against the project's stated purpose).
- **Keep order** — scene order = topic order = member order.
- **Account safety** — all YouTube calls go through the project's rate-limited tools
  (`--search`, the downloader); never call yt-dlp directly.
- **Delegate** the matching (skill) and downloading (sub-agent) so each step is isolated
  and this orchestrator only holds the plan + the file paths.
- Report the final `movie.yaml` path and the produced video location.
