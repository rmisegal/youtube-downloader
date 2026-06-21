---
name: movie-script-writer
description: >
  Author the per-scene script for the movie pipeline. Given a movie config (topic,
  description, vibe) and the song's scenario grid (structure.json from --plan-movie),
  write script.json — one scene per grid slot, each with a visual_description and a
  YouTube search_query for REAL footage. Trigger: /movie-script-writer (or invoked by
  the youtube-movie-maker orchestrator).
---

# Movie Script Writer (Skill layer)

You turn a music-video brief + the song's beat structure into a concrete **shot script**
that the pipeline can fill with real YouTube footage. You are the Skill layer of the
Three-Layer Agent Architecture (Software → **Skill** → Agent).

## Inputs
- A pipeline **config.json** (`topic`, `description`, `vibe`, `scene_target`, …).
- The **`structure.json`** the pipeline wrote during `--plan-movie`: a JSON array of
  scenario slots, each `{ index, at, until, duration, section }` (the bar-snapped cut
  grid of the leading song, tagged intro/verse/chorus/…). Path is printed by
  `--plan-movie` (usually `<build>/structure.json`).

## What to produce
Write **`script.json`** in the SAME build folder (next to `structure.json`) — a JSON
array with **exactly one object per slot**, in order:

```
[
  {
    "scenario_number": 1,
    "section": "intro",
    "start_sec": 0.0,
    "duration_sec": 2.3,
    "visual_description": "wide aerial of a city skyline at dawn, slow push-in",
    "search_query": "city skyline dawn aerial 4k"
  }
]
```

Rules:
- One scene per `structure.json` slot; copy `index→scenario_number`, `at→start_sec`,
  `duration→duration_sec`, `section` through unchanged. Do not invent extra scenes.
- Make `visual_description` match the **section energy** (calm intros, high-energy
  choruses) and tell a coherent story across the song that fits `topic`/`vibe`.
- Make `search_query` a **short, literal YouTube query** likely to return REAL stock/
  B-roll footage for that shot — concrete nouns + style words, no punctuation tricks.
- **Only real footage** — describe shots that exist on YouTube; never imply generated/
  fake imagery (out of scope and against the project's purpose).

## Why this exists
Running `--make-movie` alone lets the pipeline's LLM provider (Claude via CLI login by
default) write the script automatically. Use THIS skill when *you* (the agent) should
author the script with full control: the pipeline resumes from your `script.json` and
skips its own SCRIPT stage. After writing it, hand back to the orchestrator to run
`--make-movie` (MATCH → FETCH → BUILD → RENDER).
