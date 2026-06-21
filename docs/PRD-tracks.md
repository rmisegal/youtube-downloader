# PRD — Multi-track timeline: independent overlay tracks (titles / subtitles)

| Field | Value |
|-------|-------|
| Project | `youtube-downloader` (multi-track extension) |
| Document version | 1.05 |
| Date | 2026-06-21 |
| Status | Approved — implemented (incremental) |
| Builds on | PRD-images (timeline), PRD-beatsync (sync + effects) |

## 1. Goal
Let a playlist drive **independent, overlapping tracks** — the visual track (images/videos) plus a **title/text**
track and a **subtitle** track — **each with its own beat-timeline** (own in/out), its own in/out **transition**,
and its own **effects**, composited together. Example: an image pulses while a title slides right→left above it;
later the image changes (transition) while the text keeps moving. **All effect/transition selection reuses the
same shared code.** No runtime LLM.

## 2. Approach (incremental, two-pass)
* The **visual base** (images/videos) renders exactly as today (sync placement → concat / xfade / overlay,
  leading audio). 
* A light **overlay-tracks second pass** draws each title/subtitle element over the base via FFmpeg `drawtext`,
  each gated to its own `[at,until]`, with a move, an alpha fade, a beat bob, and a colour. The base audio is
  preserved. Text elements are sparse → the second pass is cheap.

## 3. Shared effect vocabulary
One registry drives every track: `constants.py` (transition + beat-effect names, directions), and the
selection in `transitions.resolve`/`beat_effects` (visual) — the title track reuses the **names**, **directions**
and the **BPM beat math**. Because FFmpeg cannot apply the image `zoompan` to live overlay text, the same effect
*name* maps to a text-native form: `fade`→alpha fade, `pulse`→a beat-synced bob, direction→an overlay-x/y
expression of `t`. Selection shared; only the final filter string differs per track (documented).

## 4. Schema (additive, `metadata.tracks`)
```yaml
metadata:
  leading: { kind: audio, file: 'song.mp3' }
  sync:    { enabled: true, target: video_art, mode: bar }
  tracks:
    titles:
      - { text: "HELLO", at_beat: 16, for_beats: 8, effect: pulse, transition: fade,
          direction: left, color: yellow }     # slides left, pulses, fades in/out
    subtitles:
      - { text: "chapter one", at_beat: 0, for_beats: 32, color: white, y: 0.85 }
members: [ ... visual track, unchanged ... ]
```
Timing: **beats preferred** (`at_beat`/`for_beats`, resolved against the analyzed grid) with **seconds fallback**
(`at`/`until`). The leading track is analyzed once; its beat grid feeds both the visual sync and the overlay timing.

## 5. Components
`services/playlist/track_model.py` (TrackElement/Tracks) · `loader.py` parses `metadata.tracks` ·
`services/analysis/beat_time.py` (`resolve_timing`) · `infra/playback/titles.py` (`text_drawtext`) ·
`infra/playback/overlay_tracks.py` (`build_overlay_command`) · `sync.build_overlay`/`prepare_render` ·
render wiring threads `overlay` `runner → engines → sample_stream` (second pass) · `render_route.py` extracted to
keep `sample_stream` ≤150.

## 6. Compliance (glb-quality)
SDK-first; reuse (shared effect vocabulary, the timeline/overlay machinery); ≤150-line files (render routing
extracted); ≥85% coverage; ruff clean; config/schema versioned; no secrets; uv only. Drive-safety on member files.

## 7. Verification
`uv run ruff check` · `uv run pytest --cov=src` (≥85%) · file-size ≤150 · a real render of a base + a title track
where the title text appears, **moves** (different x at two times) and fades; then a manual `--playlist-file` of a
mixed playlist showing images/video on the beat with a title sliding + pulsing **independently** above them.

## 8. Out of scope (this iteration)
Full uniform multi-track engine; per-beat text colour **cycling** (single colour / 2-colour alternate only);
`.srt` import + rich styling for subtitles (plain text first); audio-track effects beyond leading trim/fade/loop.
