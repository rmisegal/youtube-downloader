# PRD — Sampler, Per-Clip Duration & YAML Playlist (Python CLI)

| Field | Value |
|-------|-------|
| Project | `youtube-downloader` (Playlist / Sampler extension) |
| Location | `C:\25D\app\youtube-downloader` |
| Repository | https://github.com/rmisegal/youtube-downloader (public) |
| Document version | 1.03 |
| Code version (target) | 1.03 |
| Config version (target) | 1.03 |
| Date | 2026-06-20 |
| Author | Generated for rmisegal@gmail.com |
| Status | Approved — ready for extension implementation |
| Builds on | `docs/PRD-mixer.md` (v1.02 mixer), `docs/PRD.md` (base downloader) |

---

## 1. Overview & Goals

### 1.1 Purpose
Extend the v1.02 Video Mixer with three capabilities: a **sampler** that previews a folder by jumping to a
random mid-point of each clip, a **per-clip play duration** flag, and a declarative **YAML playlist** that can
**display** (live VLC), **save** (render the whole mix to one video file), and/or **stream** (local VLC
broadcast). It reuses the existing engines and infrastructure — `StreamServer`, `LibVlcPlayerMatrix`,
`Option1Engine`/`Option2Engine`, `VlcLocator`, `PlaylistEngine`, `MixerService`, `probe_duration`,
`FfmpegLocator`, `ConfigManager`, and the rate-limited `ApiGatekeeper`/`SDK.download` path.

### 1.2 Scope (one line)
> `uv run python -m ytdl (--sample-play --dir <folder> | --playlist-file <list.yaml>) [--play-for-sec N] [--mode option1|option2]`

### 1.3 Success criteria
- S1: `--sample-play --dir <folder>` plays a random mid-band 10s sample of each clip, crossfading between them, looping the folder.
- S2: `--play-for-sec N` makes each clip play N seconds before the crossfade (sampler or mix mode).
- S3: `--playlist-file list.yaml` plays and/or renders one combined file per the YAML metadata, honoring mix toggles, leading track, and loop.
- S4: Passes the full `/glb-quality-code-guidlines` audit (all 14 rules) — see §11.

### 1.4 Non-goals (v1.03)
- No GUI playlist editor; no external RTMP/Twitch/YouTube push (stream = local VLC loopback only).
- No per-pixel video alpha (Option 2 remains gapless + audio crossfade, per v1.02).
- No subtitle styling/positioning beyond insert/burn; no hardware-accel tuning.

---

## 2. Unifying Model — Segment-Aware Mixing (key refactor)

The v1.02 engines take a **flat track list + a single global** `source_mix_time`/`target_start_time`. All three
new features require **per-clip** timing, so v1.03 introduces a `MixSegment` value object as the common currency
between the segment builders (sampler / play-for-sec / YAML) and the consumers (engines / renderer):

```
# src/ytdl/services/mixer/segment.py
@dataclass(frozen=True)
class MixSegment:
    path: str
    start: float = 0.0          # in-point (seconds)
    play_seconds: float | None = None  # how long to play before the crossfade (None = full clip)
    speed: float = 1.0          # playback speed (1.0 = normal)
    resolution: str = "max"     # "max" or "WxH" / height
    subtitle: str | bool | None = None  # None/False=off, True=read embedded, "<file>"=insert that file
    effect: str = "fade"        # transition/mix effect name
```

- The sampler, `--play-for-sec`, and YAML members each produce `list[MixSegment]`.
- Engines/`MixRenderer` consume segments: per clip `-ss start -t play_seconds`; the `xfade` `offset` for clip k
  = `(cumulative play_seconds up to k) − k·crossfade`; `acrossfade` mirrors it; optional `setpts`/`atempo`
  for `speed`, `scale` for `resolution`, subtitle insert/burn per `subtitle`.
- This is **additive**: v1.02's existing `Option1Engine.run` / `Option2Engine.play_sequence` keep working;
  new segment-aware entry points are added beside them, and v1.02 tests stay green.

---

## 3. Feature 1 — `--sample-play` (Sampler)

### 3.1 CLI
```powershell
uv run python -m ytdl --sample-play --dir "C:\videos" [--play-for-sec N] [--mode option1|option2]
```

### 3.2 Behavior
- Scan `--dir` (reuse `PlaylistEngine.scan` — `SUPPORTED_VIDEO_FORMATS`, removable-drive `Test-Path` guard;
  missing dir → **exit 2**).
- For each clip, probe its duration (`probe_duration`) and seek to a **random point in the middle band**
  `[mid_band_low, mid_band_high] · duration` (config defaults 0.25–0.75) via an **injectable RNG**
  (deterministic in tests).
- Play `sample.play_seconds` (config default **10**) or `--play-for-sec` if given, then crossfade
  (video+audio) into the next clip's random mid-band sample.
- At the end of the folder, **loop by default** (`sample.loop = true`) and start over until the user stops it.
- Implemented by a `Sampler` that emits `list[MixSegment]` (`start = random mid`, `play_seconds = sample/clip`),
  routed to the chosen engine (`--mode`, default `option2`).

---

## 4. Feature 2 — `--play-for-sec N`

- A global per-clip duration: each clip plays **N seconds** (from its `start`) before the crossfade.
- Works with `--mix`, `--sample-play`, and as a default for YAML members lacking `play_time`.
- Overrides `sample.play_seconds`. Sets `MixSegment.play_seconds = N`.
- Type `float` (seconds). Default unset → fall back to config / full clip.

---

## 5. Feature 3 — `--playlist-file <file.yaml>` (Declarative YAML Playlist)

### 5.1 CLI
```powershell
uv run python -m ytdl --playlist-file "C:\lists\show.yaml"
```
New dependency: `uv add pyyaml`.

### 5.2 YAML schema (full example)
```yaml
version: "1.03"
metadata:
  source_folder: "C:/videos"        # default folder for members whose file has no path
  target_folder: "C:/out"           # where the saved/rendered output is written
  output:
    display: true                   # play live in VLC
    save: false                     # render the whole mix into ONE file in target_folder
    stream: false                   # act as streamer (local VLC broadcast)
  mix:
    video: true                     # produce the video stream
    audio: true                     # produce the audio mix
    subtitle: false                 # produce subtitles (off => not created)
  leading:
    kind: none                      # none | video | audio
    file: ""                        # leading=video: picture+length master; leading's OWN audio is MUTED,
                                    #   members supply the audio mix.
                                    # leading=audio: audio+length master; file may be audio OR a video file
                                    #   (its picture is discarded, only its sound track is used); members
                                    #   supply the video mix.
  loop: true                        # loop the whole mix; if false play once (save done once)
  summary:                          # COMPUTED/OUTPUT — filled by the tool, not required as input
    total_length_seconds: 0
    total_file_size_bytes: 0
    resolution: ""
    members: []
members:
  - id: 1                           # order in the playlist
    file: "intro.mp4"               # no path => source_folder/intro.mp4
    start_time: 12.0                # seconds into the video to start
    play_time: 10.0                 # seconds to play before mixing into the next
    playback_speed: 1.0             # default normal
    resolution: "max"               # default max resolution
    subtitle: false                 # false | true (read embedded) | "subs.srt" (insert that file)
    effect: "fade"                  # mix/transition effect
  - id: 2
    file: "C:/other/clip2.mkv"
    start_time: 0.0
    play_time: 8.0
    playback_speed: 1.25
    resolution: "1280x720"
    subtitle: "clip2.he.srt"
    effect: "fade"
```

### 5.3 Behavior
1. **Load + validate** the YAML (`PlaylistError` → **exit 8** on malformed/invalid). Validate the schema
   version, required fields, file existence (with the source-folder + removable-drive guard).
2. **Order** members by `id`; resolve each `file` (relative → `source_folder`); build `list[MixSegment]`.
3. **Mix toggles** (`metadata.mix`): only the enabled streams (video/audio/subtitle) are produced; an off
   toggle is not created.
4. **Leading track** (`metadata.leading.kind`):
   - `video` → the leading video's **picture and length** are the master. Its **own audio track MUST be muted /
     dropped** — the audio comes entirely from the members' mix (acrossfade per member defs); members supply
     audio (+subtitles). Output = one video the length of the leading video.
   - `audio` → the leading source's **audio track and length** are the master. The leading `file` MAY be a
     plain audio file **or a video file**; when it is a video file, its **picture MUST be removed/blanked** and
     **only its audio track is used** (length + sound). Members supply the **video** mix (xfade) + subtitles.
     Output length = the leading audio track's length.
   - `none` → standard segment mix; total length = sum(play_time) − (N−1)·crossfade.
5. **Output routing** (any combination of `metadata.output`):
   - `display` → live playback via the engines (VLC).
   - `save` → `MixRenderer` renders ONE file into `target_folder` (executed once even if `loop`).
   - `stream` → local VLC broadcast (Option-1 `vlc -`).
6. **Loop** (`metadata.loop`): loop the live mix when true; play once when false.
7. **Summary**: a `summary` computor fills `total_length_seconds`, `total_file_size_bytes`, `resolution`, and
   the `members` list — reported to the console and written back into the playlist's `metadata.summary`.

---

## 6. Save Renderer (`infra/playback/renderer.py` — `MixRenderer`)

The "save" engine builds a **single continuous FFmpeg graph** over N trimmed inputs and writes one file:
- Each input: `-ss <start> -t <play_seconds> -i <file>` (+ optional `scale=<resolution>`, `setpts`/`atempo`
  for `speed`, subtitle `subtitles=`/`-vf` insert per member).
- Chain `xfade=transition=<effect>:duration=<crossfade>:offset=<cumulative>` for video and `acrossfade` for
  audio, with cumulative offsets.
- **Leading-video variant:** keep the leading video's picture but **drop its audio** (`-an` on the leading
  input, or `-map` only its video); the output audio is the members' acrossfade mix, clamped/looped to the
  leading length.
- **Leading-audio variant:** take **only the audio** of the leading source (`-vn`, or `-map 0:a:0`) — even when
  that source is a video file its picture is discarded; the output video is the members' xfade mix over the
  leading audio's length.
- Output container/codecs from the `render` config block; written to `metadata.target_folder`.
- Reuses `FfmpegLocator` + `probe_duration`; subprocess injected for tests. **(Hard pipeline — see §12.)**

---

## 7. Architecture Additions (every file ≤150 code lines)

```
services/mixer/segment.py      # MixSegment dataclass
services/mixer/sampler.py      # Sampler — random-mid-band segment builder (injectable RNG; loop)
services/playlist/             # NEW package
  model.py                     # Playlist / Metadata / Output / Mix / Leading / Member dataclasses
  loader.py                    # YAML -> model + validation (PlaylistError)
  summary.py                   # compute total length / size / resolution / members
infra/playback/renderer.py     # MixRenderer (save engine)
```
- **Engines/adapters:** add segment-aware entry points to `Option1Engine`/`Option2Engine` (and
  `StreamServer`/`LibVlcPlayerMatrix`) accepting `list[MixSegment]` — additive; v1.02 tests stay green.
- **SDK (Rule 1):** add `sample_play(directory, *, play_for_sec=None, mode=None)` and
  `play_playlist(yaml_path)`; wire via `sdk/wiring.py` (`build_sampler`, `build_playlist_runner`).
- **CLI:** `--sample-play`, `--play-for-sec`, `--playlist-file` in `cli/args.py`; route in `cli/main.py`;
  cheat-sheet entries in `cli/usage.py`.
- **Reuse:** `PlaylistEngine.scan`, `shared/selection`, `FfmpegLocator`, `probe_duration`, `VlcLocator`,
  `ConfigManager`, `ApiGatekeeper`/`SDK.download` (a member `file` may be a YouTube URL → downloaded
  rate-limited to the cache, then used as a segment).

---

## 8. Configuration (version 1.03)

### 8.1 `config/setup.json` additions
```json
{
  "version": "1.03",
  "sample": {
    "play_seconds": 10,
    "mid_band_low": 0.25,
    "mid_band_high": 0.75,
    "loop": true
  },
  "render": {
    "video_codec": "libx264",
    "audio_codec": "aac",
    "container": "mp4"
  }
}
```
### 8.2 Versioning
`config/rate_limits.json` `version` → `1.03`; `ConfigManager.SUPPORTED_CONFIG_VERSIONS` += `"1.03"`;
`src/ytdl/shared/version.py __version__` → `"1.03"`. All tunables read via `ConfigManager.get` (Rule 11).

---

## 9. Exit Codes (extends 0–7 from PRD-mixer)

| Code | Meaning |
|------|---------|
| `0` | Success. |
| `2` | Bad `--dir` / missing file / usage error. |
| `7` | VLC / playback dependency missing. |
| `8` | **Invalid or malformed playlist YAML** (schema/validation error → `PlaylistError`). |
| `1` | Other / unexpected error. |

(Codes 3–6 carry over: network, unsupported, config-version, rate-limit.)

---

## 10. Dependencies

| Item | How | Notes |
|------|-----|-------|
| `pyyaml` | `uv add pyyaml` (Rule 14) | Parse the playlist YAML. |
| FFmpeg | bundled via `imageio-ffmpeg` (reused) | Render-to-file (save) + duration probe. |
| VLC / libVLC | external prerequisite (from v1.02) | Display + stream. Missing → exit 7. |

No new secrets; reuses `.env` / `.gitignore`.

---

## 11. glb-quality Compliance Matrix (all 14 rules)

| # | Rule | How the extension satisfies it |
|---|------|--------------------------------|
| 1 | SDK architecture | `sample_play`/`play_playlist` on the SDK; CLI delegates (§7). |
| 2 | OOP / no duplication | `MixSegment` shared model; reuse `PlaylistEngine`, `FfmpegLocator`, engines, `selection` (§2, §7). |
| 3 | API Gatekeeper | YouTube member URLs go through existing `ApiGatekeeper` (§7). |
| 4 | Rate-limit config | Reuses `rate_limits.json` for member downloads. |
| 5 | Queue management | Reuses `DownloadQueue` for live insertion. |
| 6 | Version control | Config + code → `1.03`; validation (§8.2). |
| 7 | TDD | Test-first; mocked FFmpeg/VLC/YAML; injectable RNG/clock (§13). |
| 8 | File size ≤150 | New modules split (`segment`/`sampler`/`model`/`loader`/`summary`/`renderer`) (§7). |
| 9 | Coverage ≥85% | Enforced via existing `fail_under`. |
| 10 | Ruff zero violations | Existing ruff config applies. |
| 11 | No hardcoded values | sample/render/playlist defaults from config (§8). |
| 12 | Config architecture | New `sample` + `render` blocks; constants in `constants.py`. |
| 13 | Secrets management | No new secrets; reuses `.env`. |
| 14 | uv package manager | `uv add pyyaml`; all commands via uv. |

---

## 12. Risks / Out of Scope (v1.03)

- **Continuous N-clip `xfade` render** (save) and **leading-track compositing** are the complex pieces.
  Documented **build order: display first, then save**; leading-track save is the most intricate path.
- **External RTMP/streaming** (YouTube/Twitch ingest), GUI playlist editor, subtitle styling/positioning, and
  hardware-accel tuning are **out of scope** — `stream` in v1.03 is the local VLC loopback only.
- Per-segment `speed`/`resolution` changes interact with `xfade` (inputs must share size/SAR/fps); the
  renderer normalizes inputs (`scale`/`fps`/`setsar`) before `xfade`.

---

## 13. Testing & Verification

- Mirror new modules under `tests/unit/{services/mixer,services/playlist,infra/playback,sdk,cli}`.
- **Mock all boundaries**: YAML via in-memory dicts / `tmp_path` files, FFmpeg & VLC subprocess handles,
  `probe_duration`, and an **injectable RNG** (sampler) and clock. **No real render, playback, or network.**
- Validate: malformed YAML → `PlaylistError`/exit 8; sampler picks deterministic mid-band starts under a seeded
  RNG; `--play-for-sec` overrides; mix toggles gate streams; leading-kind selects the right master; `MixRenderer`
  builds the expected FFmpeg argv (offsets/`-ss`/`-t`/codecs); summary computes length/size/resolution.
- Gates: `uv run ruff check`, `uv run pytest --cov=src` (≥85%), file-size ≤150 script, uv-only.
- Manual (needs VLC): `--sample-play --dir .\downloads`; `--playlist-file sample.yaml` with `output.save: true`
  → one rendered file appears in `target_folder`; with `display: true` → VLC plays the mix.
