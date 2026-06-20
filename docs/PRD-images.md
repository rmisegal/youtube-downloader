# PRD — Image Support & Transitions for the Playlist Mixer

| Field | Value |
|-------|-------|
| Project | `youtube-downloader` (Playlist mixer — image extension) |
| Repository | https://github.com/rmisegal/youtube-downloader |
| Document version | 1.04 |
| Playlist schema | 1.04 |
| Date | 2026-06-20 |
| Status | Approved — implemented |
| Builds on | `docs/PRD-mixer.md`, `docs/PRD-playlist` behavior (leading audio) |

## 1. Overview & goals
Let a playlist place **still images** on the **leading-audio timeline**: each image pops up at an absolute
soundtrack time, disappears at an end timestamp, and animates with a transition (fade / zoom / pan, **random by
default**). Images **mix with videos** and **overlay** running video (later member on top). The leading audio is
the soundtrack and follows the visuals (shorter → fade-out; longer → crossfade-loop — the existing rule). Reuses
the `--sample-play` prep→render-one-file→one-VLC pipeline; obeys `/glb-quality-code-guidlines`.

**Non-goals (this release):** title/text overlay (deferred), `save`/`stream` of an image timeline (display
only for now), the full 40+ xfade library per member, audio ducking, easing curves.

## 2. Architecture (reuse-first; new files keep `renderer.py` ≤150)
```
playlist YAML(1.04) ─► loader/model ─► MixSegment(kind/at/until/transition/direction)
                                         │
PlaylistRunner._display ─► Option1Engine.run_segments(timeline=True) ─► stream_samples
   SamplePrep.build_command  (image: -loop 1 + transitions.image_vfilter + silent audio → uniform .ts)
   timeline.build_timeline_command  (black base + overlay=enable=between(t,at,until) per clip + leading audio)
   → render ONE mix.mp4 → ONE VLC (auto-plays, replayable)
```
- **Reused unchanged:** playlist loader/model/runner, `SamplePrep` (silent-audio `anullsrc` path),
  `renderer.looped_leading` + leading trim/fade, `VlcLocator`, the one-file→one-VLC shell, `MixRenderer`
  helpers (`_canvas/_fps/_ffmpeg/_codec_out`).
- **New:** `infra/playback/transitions.py` (per-image `zoompan`/`fade` + `random`), `infra/playback/timeline.py`
  (absolute-time overlay compositor; takes the `MixRenderer` like `renderer_leading` does — no config dup).

## 3. YAML schema (version `1.04`)
Member gains: `type: video|image` (default `video`), `at` (timeline start s), `until` (timeline end s; image
duration = `until−at`), `transition` (name or `random`, default `random`), `direction` (`left|right|up|down`).
Old `1.03` playlists still load.

## 4. Transitions
`fade`, `zoomin`, `zoomout`, `panleft|panright|panup|pandown`, `random` (default → picks one at render via an
injectable RNG). zoom/pan use FFmpeg `zoompan` (Ken Burns); every image also gets a short edge fade so
overlapping timeline slots blend. Images: `.jpg .jpeg .png .webp .bmp .gif`.

## 5. Behavior
Timeline length = `max(at + duration)` over visuals. Each prepped clip is overlaid at its `at` via
`setpts=PTS+at/TB` + `overlay=enable='between(t,at,until)'`; later `id` overlays earlier (image over video).
Leading audio is looped (`looped_leading`) when short and trimmed + faded to the timeline length. Removable-drive
guard applies to image files. A timeline playlist always renders ONE file in ONE VLC (Option-2 matrix bypassed).

## 6. Exit codes
Unchanged: `8` invalid playlist YAML; `7` VLC missing. Image files that don't exist → `PlaylistError` (8).

## 7. Compliance matrix (14 rules)
| # | Rule | How |
|---|------|-----|
| 1 | SDK | `sdk.play_playlist` → runner; CLI unchanged |
| 2 | OOP/no-dup | reuses SamplePrep/renderer/leading/runner; transitions+timeline are the only new logic |
| 3–5 | Gatekeeper/limits/queue | URL image/video members still download via the rate-limited path |
| 6 | Versioning | playlist schema `1.04` (old still supported) |
| 7 | TDD | tests for transitions, image prep, timeline, loader, runner routing + real render |
| 8 | ≤150 lines | new modules small; `renderer.py` untouched |
| 9 | ≥85% coverage | maintained (~98%) |
| 10 | Ruff | zero violations |
| 11 | No hardcoded | canvas/fps/codec from config; transition names in `constants.py` |
| 12 | Config arch | `constants.py` formats/transitions; `render.*`/`playback.*` config |
| 13 | Secrets | none added |
| 14 | uv | unchanged toolchain |

## 8. Verification
`uv run ruff check` · `uv run pytest --cov=src` (≥85%) · file-size ≤150 · a real (no-GUI) render of a YAML with
2 images + leading audio → one mp4 whose duration = visual span with video+audio. Manual `--playlist-file` run
opens one VLC showing images animating at their timeline slots over the soundtrack.
