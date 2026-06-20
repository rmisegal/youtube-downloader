# PRD — Beat-Sync: Audio Rhythm/Structure Analyzer + Music-Synced Playlists

| Field | Value |
|-------|-------|
| Project | `youtube-downloader` (Beat-Sync extension) |
| Repository | https://github.com/rmisegal/youtube-downloader |
| Document version | 1.05 |
| Config / playlist schema | 1.05 |
| Date | 2026-06-20 |
| Status | Approved — ready for implementation |
| Builds on | `docs/PRD-images.md` (timeline compositor), playlist leading-audio |

## 1. Overview & goal
Analyze the **leading music track** and extract multi-tier rhythm/structure cut-points (beats, bars/downbeats,
phrases, sections), then **auto-snap playlist transitions** to them — so an image/video slideshow syncs to the
song like a professional editor cut it. Two deliverables: **(A)** a standalone analyzer (`--analyze` → JSON
cut-points) and **(B)** a playlist **sync mode** that auto-places members on the planned cut-points and renders
via the existing timeline compositor.

## 2. Engine decision (validated)
- **`librosa` (always, in-process)** — pip-installable, runs on our Python 3.12. Verified on a real 188s mp3:
  103.4 BPM, 294 beats, 819 onsets. Provides beats/onsets/tempo and section segmentation (recurrence/Laplacian).
- **Performance fix (mandatory):** `librosa.load` on mp3 took **25.5s** (decode+resample) — over the 10s NFR.
  The analyzer first **decodes the audio to 22.05 kHz mono WAV via the bundled `imageio-ffmpeg`** (≈1–2s, reuses
  `FfmpegLocator`), then loads the WAV. Brings end-to-end well under 10s for a 4-min track.
- **`madmom` (optional sidecar)** — best for true ML downbeats/bars but requires Python ≤3.9 and won't build on
  Windows/3.12. Wired as a **subprocess sidecar** (`uv run --python 3.9 --with madmom tools/madmom_downbeats.py`)
  behind a pluggable `DownbeatBackend`; `auto` uses it when it runs, else librosa-derived downbeats. Never a main dep.

## 3. Analysis tiers (PRD source §3)
| Tier | What | How |
|------|------|-----|
| Beats & onsets (micro) | pulses + transients, BPM | librosa `beat_track`, `onset_detect`, `onset_strength` |
| Bars / downbeats (mid) | first beat of each measure | group beats by `meter` (4/4); downbeat = strongest-onset beat of the group; or madmom sidecar |
| Phrases (macro) | 4/8-bar sentences | group bars by `phrase_bars`; boundaries refined by onset-novelty dips |
| Sections (structural) | Intro/Verse/Chorus/Build/Outro | librosa segmentation (recurrence + agglomerative/Laplacian) + a heuristic **labeler** (energy/position) |

Section labels are heuristic (energy + position), not ground-truth ML — documented as approximate.

## 4. The Context-Aware Cut Planner (the centerpiece)
Sync does **not** pick a transition tier per frame at random. The **Section level dictates the cut rhythm** for
each segment (config-driven `analysis.section_rules`):

| Section | Lead cut tier | Feel | Rhythm break |
|---------|---------------|------|--------------|
| Intro / Outro | **Phrase** (slow) | curiosity / relaxation | last bar before the next section |
| Verse | **Bar / Downbeat** | steady narrative flow | a full phrase for emphasis |
| Build-up | **Beat** (accelerating) | rising tension | accelerate from mid-build to the climax |
| Chorus / Drop | **Beat / double-beat** | energetic explosion | vary the 4th bar to "breathe" |

Plus **phrase-end fills**: near a phrase boundary, if onset density spikes (a drum fill), insert **3–4 quick
beat cuts** before the next bar — "visual punctuation." `CutPlanner` is pure logic (sections + grid → ordered
cut timeline) → fully unit-testable without DSP.

## 5. Input / output (PRD source §4)
**Input:** `audio_path` (.mp3/.wav/.flac), `analysis_levels` (`BEAT|BAR|PHRASE|SECTION`), `target_fps`.
**Output JSON** (`frame_index = round(t * target_fps)`), per the source schema plus section `label`s and the
planned cut list:
```json
{ "metadata": { "file_name": "...", "duration_seconds": 188.2, "global_bpm": 103.4, "target_fps": 30.0 },
  "cut_points": {
    "beats":   [ { "timestamp_sec": 15.604, "frame_index": 468, "confidence": 0.94 } ],
    "bars":    [ { "timestamp_sec": 15.604, "frame_index": 468, "bar_index": 1 } ],
    "phrases": [ { "timestamp_sec": 15.604, "frame_index": 468, "phrase_type": "Phrase_A_Start" } ],
    "sections":[ { "start_sec": 0.0, "end_sec": 15.6, "label": "Intro" } ] },
  "cut_plan":  [ { "timestamp_sec": 0.0, "tier": "phrase", "section": "Intro" } ] }
```
CSV export is also offered (`--format csv`).

## 6. Architecture (reuse-first)
```
CLI --analyze ─► SDK.analyze_audio ─► AudioAnalyzer ─► JSON
playlist metadata.sync ─► PlaylistRunner sync pre-pass:
   leading audio ─► AudioAnalyzer ─► CutPlanner ─► assign members at/until ─► existing timeline compositor ─► one VLC
```
New package **`src/ytdl/services/analysis/`** (files ≤150 each): `analyzer.py` (orchestrator; injectable
librosa/ffmpeg/backend), `audio_io.py` (ffmpeg-decode→wav + librosa load), `beats.py`, `structure.py`
(segment+label), `grid.py` (bars/phrases), `downbeat_backend.py` (`LibrosaDownbeats` + `MadmomSidecar`),
`cut_planner.py` (pure rules engine), `export.py` (JSON/CSV). Reuses `FfmpegLocator`, the injected-subprocess
pattern, `ConfigManager`. **SDK:** `analyze_audio(...)` + `build_analyzer` in `sdk/wiring.py`. **Playlist:**
`metadata.sync {enabled, mode: auto|beat|bar|phrase|section, target_fps}`; a **sync pre-pass** in
`PlaylistRunner.run` assigns `at`/`until` from the plan (cycling media to fill the track) via
`dataclasses.replace`, then the **existing** timeline render runs. **CLI:** `--analyze <audio>` + `--fps`,
`--levels`, `-o`, `--format`. **Config** `analysis.*` (fps, levels, meter, phrase_bars, downbeat_backend,
section_rules, fill_on_phrase_end). **Errors:** `AudioAnalysisError(YtdlError)` + a CLI exit code.

## 7. Non-functional (PRD source §5)
- **Precision** ±20 ms (frame-accurate). **Performance** < 10 s for a 4-min track (via the ffmpeg-predecode).
- Deps: `librosa` (added); madmom sidecar only. Config-versioned; schema `1.05` (old still load).

## 8. glb-quality compliance (14 rules)
| # | Rule | How |
|---|------|-----|
| 1 | SDK | `analyze_audio` + sync via `play_playlist`; CLI delegates |
| 2 | OOP/no-dup | reuses ffmpeg/timeline/leading/loader; analyzer split into small single-purpose modules |
| 3–5 | Gatekeeper/limits/queue | unaffected (local DSP); URL audio still downloads via the rate-limited path |
| 6 | Versioning | config + playlist schema `1.05` |
| 7 | TDD | DSP mocked; `cut_planner`/`export` pure-logic tested; real-audio smoke in verification |
| 8 | ≤150 lines | new modules small; `renderer.py` untouched |
| 9 | ≥85% coverage | maintained |
| 10 | Ruff | zero violations |
| 11 | No hardcoded | fps/tiers/meter/section-rules from config |
| 12 | Config arch | `analysis.*` block + `constants.py` tier names |
| 13 | Secrets | none added |
| 14 | uv | `uv add librosa`; madmom via `uv run --python 3.9` sidecar |

## 9. Verification
`uv run ruff check` · `uv run pytest --cov=src` (≥85%) · file-size ≤150 · real:
`uv run python -m ytdl --analyze "C:\\Users\\gal-t\\Downloads\\0\\new-start.mp3" --fps 30 -o beats.json`
→ JSON with beats/bars/phrases/sections, BPM>0, runtime <10s; a `sync` photo playlist renders one mp4 whose
member `at` times equal planned cut-points.

## 10. Future (PRD source §6 — out of scope here)
Premiere `.edl` / After Effects JSX marker export (Phase II); standalone moviepy stitching (Phase III — our
timeline renderer already stitches); BeatNet/other ML backends; ground-truth section labeling.
