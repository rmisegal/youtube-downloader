# youtube-downloader

A Windows PowerShell command-line tool that, given a single YouTube URL, downloads the
**video as mp4**, and/or extracts the **audio as mp3**, and/or downloads the **subtitles as `.srt`**
— in any combination — using [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) with FFmpeg supplied by
[`imageio-ffmpeg`](https://pypi.org/project/imageio-ffmpeg/).

The authoritative specification lives in [`docs/PRD.md`](docs/PRD.md) and
[`docs/PLAN.md`](docs/PLAN.md).

---

## Requirements

- **Python ≥ 3.10**
- **[uv](https://docs.astral.sh/uv/)** (the only supported package manager — never `pip`)
- **No system FFmpeg install** — the FFmpeg binary is bundled via `imageio-ffmpeg` and located
  automatically at runtime.
- **No GPU / CUDA** — download is I/O-bound, mp3 extraction uses FFmpeg on CPU, and subtitles are
  plain text. GPU is only relevant to a future, out-of-scope transcription feature (see below).

---

## Install

```powershell
uv sync
```

This resolves and installs all runtime and dev dependencies from the committed `uv.lock`. Do **not**
use `pip` or `requirements.txt`.

---

## Usage

Invoke from Windows PowerShell. The general form is:

```powershell
uv run python -m ytdl "<URL>" [--video] [--audio] [--subs] [-o DIR] [-n NAME] [--resolution H] [--sub-lang L]
```

### Examples

Download the video as mp4 (default when no mode flag is given):

```powershell
uv run python -m ytdl "<URL>"
```

Extract audio as mp3:

```powershell
uv run python -m ytdl "<URL>" --audio
```

Download English subtitles as `.srt`:

```powershell
uv run python -m ytdl "<URL>" --subs --sub-lang en
```

Combine all three modes into a chosen folder and base name, capped at 720p:

```powershell
uv run python -m ytdl "<URL>" --video --audio --subs -o .\downloads -n myfile --resolution 720
# Produces: .\downloads\myfile.mp4, .\downloads\myfile.mp3, .\downloads\myfile.en.srt
```

Print the code + config version and exit:

```powershell
uv run python -m ytdl --version
```

Show the run-command cheat-sheet (all commands with examples) and exit:

```powershell
uv run python -m ytdl --command
```

`--video`, `--audio`, and `--subs` are **independent toggles**; any combination is valid in a single
run, and the video is fetched only once. If **none** of them is supplied, the tool defaults to
`--video`.

---

## Flags

Taken verbatim from the argparse definition in
[`src/ytdl/cli/args.py`](src/ytdl/cli/args.py):

| Flag | Meaning | Default |
|------|---------|---------|
| `url` (positional) | The YouTube video URL. | required (usage error if omitted) |
| `--video` | Download best-quality mp4 (merged video+audio). | off — but auto-enabled if no mode flag is given |
| `--audio` | Extract mp3 audio. | off |
| `--subs` | Download subtitles as `.srt`. | off |
| `-o`, `--output-dir` | Output folder (created if missing). | from config (`./downloads`) |
| `-n`, `--name` | Output base file name (no extension). | video title (`%(title)s`) |
| `--resolution` | Max video height, e.g. `1080` or `720` (int). | best available |
| `--sub-lang` | Subtitle language code. | `en` |
| `--no-playlist` | For a list/mix URL, download only the single video. | off |
| `--playlist-items` | Download only these items, e.g. `1,3,5` or `1-5` (skips the prompt). | — |
| `--version` | Print code + config version and exit. | — |
| `-command`, `--command` | Show the run-command cheat-sheet (commands + examples) and exit. | — |

---

## Output naming

Files are written into the output directory using the chosen base name plus a mode-specific
extension:

| Mode | Output file |
|------|-------------|
| Video | `<name>.mp4` |
| Audio | `<name>.mp3` |
| Subtitles | `<name>.<lang>.srt` |

When `-n`/`--name` is omitted, the base name defaults to the video title (`%(title)s`). The output
directory is created automatically if it does not exist (idempotent — no error if it already does).

---

## Configuration overview

All tunables are **config-driven** — there are no hardcoded values in the code. Each tunable is read
via `ConfigManager.get("a.b", default)`; `src/ytdl/constants.py` holds only true constants. Both
config files carry `"version": "1.03"`, validated at startup against the supported versions; a
mismatch raises `ConfigVersionError` (exit code 5).

### `config/setup.json` (version 1.03)

| Key | Purpose |
|-----|---------|
| `paths.output_dir` | Default output folder (`./downloads`). Overridden by `-o`. |
| `network.js_runtime` | JS runtime for yt-dlp: `auto` (detect deno/node/bun/quickjs on PATH), a specific name, or `none`. |
| `defaults.resolution` | Default max video height (`null` = best available). Overridden by `--resolution`. |
| `defaults.sub_lang` | Default subtitle language (`en`). Overridden by `--sub-lang`. |
| `audio.codec` / `audio.quality` | Audio codec (`mp3`) and bitrate (`192`). |
| `subtitles.format` / `subtitles.include_auto` | Subtitle format (`srt`) and include auto-generated (`true`). |
| `ffmpeg.location` | FFmpeg locator strategy (`auto` = resolve via `imageio-ffmpeg`). |

### `config/rate_limits.json` (version 1.03) — avoiding YouTube blocks

YouTube does not publish hard download quotas; abuse triggers **HTTP 429 (Too Many Requests)** and
temporary IP/account throttling. This tool defends the account two ways, both fully config-driven:

**1. In-download pacing** (passed to yt-dlp on every download) under
`rate_limits.services.youtube.download`:

| Key | Purpose | Default |
|-----|---------|---------|
| `limit_rate` | Max download bandwidth (→ yt-dlp `ratelimit`). | `5M` |
| `throttled_rate` | Re-extract if speed drops below this (→ `throttledratelimit`). | `100K` |
| `sleep_requests_seconds` | Pause between metadata requests (→ `sleep_interval_requests`). | `1.0` |
| `sleep_interval_seconds` / `max_sleep_interval_seconds` | Randomized pause before each download (→ `sleep_interval` / `max_sleep_interval`). | `3.0` / `8.0` |
| `concurrent_fragments` | Parallel fragment downloads (→ `concurrent_fragment_downloads`). | `1` |
| `retries` / `fragment_retries` | yt-dlp retry counts. | `10` / `10` |

**2. Persistent quota ledger** (`UsageTracker`, enforced in the gatekeeper before every request,
counted across runs in `config/.usage_state.json`):

| Key | Purpose | Default |
|-----|---------|---------|
| `rate_limits.services.youtube.requests_per_minute` | Per-minute request cap. | `10` |
| `rate_limits.services.youtube.requests_per_hour` | Per-hour cap. | `200` |
| `rate_limits.services.youtube.requests_per_day` | Per-day cap. | `1000` |
| `rate_limits.services.youtube.requests_per_month` | Per-month cap. | `10000` |
| `rate_limits.services.youtube.concurrent_max` | Max concurrent requests. | `1` |

When a cap would be exceeded — or YouTube returns 429 — the tool stops with a clear
`RateLimitExceededError` (**exit code 6**) instead of hammering YouTube and risking a block. Queue
keys (`queue.max_depth`, `drain_interval_seconds`, `timeout_seconds`, `overflow_strategy`) are unchanged.

> Tune these in `config/rate_limits.json` — raise caps/bandwidth at your own risk, or lower
> them (e.g. `sleep_interval_seconds: 60`, `max_sleep_interval_seconds: 120`) for bulk jobs to stay
> well under YouTube's radar.

> **Fathom note:** The Fathom rate-limit keys referenced by the guideline are **N/A** here; the same
> versioned rate-limit/queue structure is applied to YouTube as the throttled external service.

---

## Playlists & mixes

If the URL belongs to a playlist or mix (`...&list=...` or `/playlist?list=...`), the tool first shows
the **number of available items** and asks whether to download **all**, **select** specific items, or
**only this video**. For "select", it lists the entries numbered and you enter the numbers
comma-separated (e.g. `1,3,5`; ranges like `2-4` work too).

Non-interactively (piped/CI), or with flags, no prompt appears:
- `--no-playlist` → only the single video,
- `--playlist-items 1,3,5` → just those items,
- otherwise a `watch?v=...&list=...` URL defaults to the single video and a bare playlist URL to all.

## JavaScript runtime

yt-dlp needs a JS runtime to extract some YouTube formats. The tool auto-detects **deno / node / bun /
quickjs** on your PATH and passes it to yt-dlp (`network.js_runtime: "auto"`), which removes the
"No supported JavaScript runtime could be found" warning. Installing one (e.g. Node.js) is recommended
for full format availability.

---

## Video mixer / VJ mode (`--mix`)

Beyond downloading, the tool can run a **real-time VJ player** that plays a folder of videos back-to-back
with **crossfade transitions** of video and audio. See `docs/PRD-mixer.md` for the full spec.

**Prerequisite:** **VLC Media Player** must be installed (https://www.videolan.org/) — it is a desktop app,
not a pip package. `python-vlc` is installed automatically via `uv sync`. If VLC is missing, mix mode prints
a clear message and exits with **code 7**.

```powershell
# Mix a folder (dual-libVLC gapless engine, random order — defaults)
uv run python -m ytdl --mix --dir "C:\videos"

# True FFmpeg crossfade engine, manual track picker, 2-second crossfade
uv run python -m ytdl --mix --dir "C:\videos" --mode option1 --selection manual --crossfade-time 2

# Set the crossfade mix points: mix OUT of the source at 30s, start the target at its 10s mark
uv run python -m ytdl --mix --dir "C:\videos" --source-mix-time 30 --target-start-time 10
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--mix` | off | Switch to mixer / VJ playback mode. |
| `--dir` | required | Folder of local videos (`.mp4 .mkv .mov .avi`). |
| `--mode` | `option2` | `option1` (FFmpeg `xfade`/`acrossfade` → VLC — **true video+audio crossfade**) or `option2` (dual-libVLC gapless switching + audio crossfade). |
| `--selection` | `random` | `random` (infinite shuffle) or `manual` (numbered picker; comma-separated, ranges like `2-4`). |
| `--crossfade-time` | `3` | Crossfade overlap window in seconds. |
| `--source-mix-time` | source end | Seconds into the **source** clip where the crossfade begins (default = `duration − crossfade`). |
| `--target-start-time` | `0` | In-point (seconds) where the **target** clip starts. |

**Two engines:**
- **Option 1 (true crossfade):** FFmpeg builds an `xfade`+`acrossfade` composite and pipes it as `mpegts`
  into a standalone VLC (`vlc -`) — a seamless, un-seekable live broadcast with real per-frame video+audio blend.
- **Option 2 (gapless switching):** two libVLC players double-buffer; the idle deck pre-seeks the next track
  to `--target-start-time`, and at the source's `--source-mix-time` the decks hand off with an **audio**
  crossfade. *libVLC cannot alpha-composite two video windows, so Option 2 does not do per-pixel video blending
  — use Option 1 for that.*

YouTube URLs can be hot-injected into a running mix; they are downloaded through the same rate-limited
`ApiGatekeeper` path, so playback never bypasses the download safety guards. Mix paths on removable drives
(`D:`/`H:`) are checked with a mount guard before scanning (missing drive → exit 2, never a hang).

All playback defaults live in `config/setup.json` under `playback` (`default_mode`, `default_selection`,
`crossfade_duration_seconds`, `source_mix_time_seconds`, `target_start_time_seconds`, `supported_video_formats`).

---

## Sampler & YAML playlists

Two further playback modes build on the mixer: a **sampler** that previews a folder by jumping to a random
mid-point of each clip, and a declarative **YAML playlist** that can display, save, and/or stream a mix.
See `docs/PRD-playlist.md` for the full spec.

**Prerequisites:** **VLC Media Player** is required for `display` and `stream` (the same desktop install as
mix mode — missing VLC → exit **7**). The `save` renderer uses **FFmpeg**, which is bundled via
`imageio-ffmpeg` (installed by `uv sync`) — no separate FFmpeg install is needed.

### Sampler — `--sample-play`

```powershell
# Crossfade a random mid-band 10s sample of each clip in the folder, looping
uv run python -m ytdl --sample-play --dir "C:\\videos"

# Play each sample for 6 seconds instead, using the FFmpeg-crossfade engine
uv run python -m ytdl --sample-play --dir "C:\\videos" --play-for-sec 6 --mode option1
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--sample-play` | off | Preview `--dir`: crossfade a random mid-band sample of each clip, looping the folder. |
| `--dir` | required | Folder of local videos to sample. |
| `--play-for-sec` | unset | Per-clip play duration in seconds (float) before the crossfade. Overrides the sampler default. Applies to the sampler and as the default for YAML members lacking `play_time`. |
| `--mode` | `option2` | Playback engine (`option1` FFmpeg true crossfade, or `option2` dual-libVLC) — same as mix mode. |

For each clip the sampler probes its duration and seeks to a random point in the middle band
(config `sample.mid_band_low`–`sample.mid_band_high`, defaults `0.25`–`0.75`), plays
`sample.play_seconds` (config default **10**) — or `--play-for-sec` if given — then crossfades into the
next clip's sample. At the end of the folder it **loops by default** (`sample.loop`) until you stop it.

### Declarative playlists — `--playlist-file`

```powershell
uv run python -m ytdl --playlist-file "C:\\lists\\show.yaml"
```

A playlist is a YAML file describing a mix: where the clips live, how each is trimmed/sped/styled, an
optional **leading** master track, and how the result is routed (display / save / stream). A worked example
lives at [`docs/examples/playlist.yaml`](docs/examples/playlist.yaml).

```yaml
version: "1.03"
metadata:
  source_folder: "C:/videos"        # default folder for members whose file has no path
  target_folder: "C:/out"           # where the saved/rendered output is written
  output:
    display: true                   # play live in VLC
    save: false                     # render the whole mix into ONE file in target_folder
    stream: false                   # act as streamer (local VLC loopback broadcast)
  mix:
    video: true                     # produce the video stream
    audio: true                     # produce the audio mix
    subtitle: false                 # produce subtitles (off => not created)
  leading:
    kind: none                      # none | video | audio
    file: ""                        # leading master file (see "Leading semantics" below)
  loop: true                        # loop the live mix; if false play once (save is done once either way)
  summary:                          # COMPUTED OUTPUT — filled by the tool, not required as input
    total_length_seconds: 0
    total_file_size_bytes: 0
    resolution: ""
    members: []
members:
  - id: 1                           # order in the playlist (members are sorted by id)
    file: "intro.mp4"               # bare name (no separator) => source_folder/intro.mp4
    start_time: 12.0                # seconds into the clip to start
    play_time: 10.0                 # seconds to play before mixing into the next clip
    playback_speed: 1.0             # 1.0 = normal
    resolution: "max"              # "max" or "WxH"
    subtitle: false                 # false | true (read embedded) | "subs.srt" (insert that file)
    effect: "fade"                  # mix / transition effect
  - id: 2
    file: "C:/other/clip2.mkv"      # absolute path is used as-is
    start_time: 0.0
    play_time: 8.0
    playback_speed: 1.25
    resolution: "1280x720"
    subtitle: "clip2.he.srt"
    effect: "fade"
```

**Schema fields**

| Block | Field | Default | Meaning |
|-------|-------|---------|---------|
| top | `version` | required | Must be `"1.03"` (the only supported playlist version). |
| `metadata` | `source_folder` | `""` | Folder prepended to member files that carry no path separator. |
| `metadata` | `target_folder` | `""` | Destination folder for the `save` render. |
| `metadata.output` | `display` / `save` / `stream` | `true` / `false` / `false` | Output routing (any combination). |
| `metadata.mix` | `video` / `audio` / `subtitle` | `true` / `true` / `false` | Per-stream toggles; an off stream is not produced. |
| `metadata.leading` | `kind` / `file` | `none` / `""` | Leading master track (see below). |
| `metadata` | `loop` | `true` | Loop the live mix; `false` plays once. |
| `metadata.summary` | — | computed | Filled by the tool (length / size / resolution / members) — not required as input. |
| `members[]` | `id` | required | Order key — members are sorted by `id`. |
| `members[]` | `file` | required | Bare name → `source_folder/<file>`; a path or `http(s)://` URL is used as given (URLs are downloaded). |
| `members[]` | `start_time` | `0.0` | In-point (seconds). |
| `members[]` | `play_time` | unset | Seconds to play before the crossfade (falls back to `--play-for-sec` / config / full clip). |
| `members[]` | `playback_speed` | `1.0` | Playback speed. |
| `members[]` | `resolution` | `"max"` | `"max"` or `"WxH"`. |
| `members[]` | `subtitle` | none | `false` (off) / `true` (read embedded) / `"<file>"` (insert that file). |
| `members[]` | `effect` | `"fade"` | Mix / transition effect name. |

**Leading semantics** (`metadata.leading.kind`)

- `none` — standard segment mix; total length = sum of member `play_time` minus the crossfade overlaps.
- `video` — the leading video's **picture and length** are the master. Its **own audio track is muted /
  dropped**; the audio comes entirely from the members' mix. Output is one video the length of the leading
  video.
- `audio` — the leading source's **audio track and length** are the master. The `file` may be a plain audio
  file **or a video file** — when it is a video file, its **picture is discarded and only its audio track is
  used**. The members supply the **video** mix. Output length = the leading audio's length.

**Output modes** (`metadata.output` — any combination)

- `display` → live playback through the VLC engines.
- `save` → the `MixRenderer` renders the whole mix into **one file** in `target_folder` via FFmpeg. This is
  done **once even when `loop` is true**.
- `stream` → local VLC loopback broadcast (Option-1 `vlc -`). No external RTMP/YouTube/Twitch push.

**Exit code 8** — an invalid or malformed playlist YAML (bad parse, not a mapping, missing `version`,
unsupported version, missing required member `id`/`file`, or a member file that cannot be found) raises a
`PlaylistError` and the CLI exits with **code 8**. (Missing VLC for display/stream still exits **7**.)

---

## Images & transitions (timeline overlay)

A playlist member can be a **still image** (`type: image`) placed on the **leading-audio timeline**: it pops
up at an absolute soundtrack time (`at`), disappears at its `until` timestamp, and animates with a transition.
Images can be **mixed with videos** and a later member **overlays** an earlier one (so an image sits on top of
a running video). The leading audio is the soundtrack and follows the visuals — if the visuals are **shorter**
than the song it **fades out** at the end; if **longer**, the song **crossfade-loops** to fill (same rule as
the video mix). Use playlist **`version: "1.04"`**.

```yaml
version: "1.04"
metadata:
  source_folder: 'C:\media'
  output:  { display: true }
  mix:     { video: true, audio: false }     # members contribute picture only
  leading: { kind: audio, file: 'C:\media\song.mp3' }   # the soundtrack
members:
  - { id: 1, type: video, file: clip.mp4,  at: 0,  start_time: 25, play_time: 30 }
  - { id: 2, type: image, file: cover.jpg, at: 10, until: 18, transition: random }
  - { id: 3, type: image, file: band.png,  at: 16, until: 24, transition: zoomin }
```
Run it (opens ONE VLC, auto-plays, replayable):
```powershell
uv run python -m ytdl --playlist-file "C:\media\photo-mix.yaml"
```

**Image member keys:** `type: image`, `at` (timeline start, s), `until` (timeline end, s; duration = `until−at`),
`transition`, `direction`.

**Transitions** (`transition:`) — `random` is the **default**:

| Name | Effect |
|------|--------|
| `fade` | fade in/out only |
| `zoomin` / `zoomout` | Ken-Burns zoom (FFmpeg `zoompan`) |
| `panleft` / `panright` / `panup` / `pandown` | slow pan across the image |
| `random` | picks one of the above at render time (default) |

Every image also gets a short fade-in/out so overlapping timeline slots blend. Supported image formats:
`.jpg .jpeg .png .webp .bmp .gif`. Implementation reuses the `--sample-play` pipeline (each member is prepped
to a uniform clip, then composited), so playback is one VLC window, auto-playing and replayable.

> **Notes:** `save`/`stream` of an image **timeline** is a follow-up — use `display` for now (save is skipped
> with a warning). A **title/text overlay** above images and videos is also planned (deferred).

---

## Music sync — beat analyzer + auto-placed transitions (PRD-beatsync)

Analyze the **leading song** and snap playlist transitions to the music. Two ways in:

**1. Standalone analyzer (`--analyze`)** — export rhythm/structure cut-points to JSON/CSV for an NLE or your
own tooling:
```powershell
uv run python -m ytdl --analyze "C:\media\song.mp3" --fps 30 -o beats.json
# --levels beat,bar,phrase,section   --format json|csv
```
Output: `metadata` (bpm, duration, target_fps, `device`, `gpu_available`) + `cut_points.{beats,bars,phrases,
sections}` with `timestamp_sec` **and** `frame_index = round(t*fps)`. Engine is **librosa** (CPU; an
ffmpeg-predecode keeps a 4-min track under ~10s). Section labels (Intro/Verse/Chorus/…) are heuristic.

**2. Playlist `metadata.sync`** — auto-place members on the planned cut-points and **fit each transition to the
music**:
```yaml
version: "1.05"
metadata:
  source_folder: 'C:\media\photos'
  output:  { display: true }
  mix:     { video: true, audio: false }
  leading: { kind: audio, file: 'C:\media\song.mp3' }   # the soundtrack to follow
  sync:    { enabled: true, mode: auto }                 # auto = context-aware planner
members:
  - { id: 1, type: image, file: a.jpg }                 # at/until are assigned by the planner
  - { id: 2, type: image, file: b.jpg }                 # members cycle across the cut-points
  - { id: 3, type: image, file: c.jpg }
```

**Context-aware planner (`mode: auto`)** — the **section** dictates the cut rhythm (config
`analysis.section_rules`): Intro/Outro → **phrase** (slow), Verse → **bar** (steady), Build-up/Chorus → **beat**
(energetic), plus phrase-end **drum-fill** bursts. Or force a fixed grid with `mode: beat|bar|phrase|section`.

**Transitions fit the sync type** — each cut carries its tier/section, so the placer picks a matching effect
(config `analysis.tier_transitions` + `analysis.section_transitions`), including **beat-reactive** effects that
move *in time with the BPM*:

| Effect | Motion | Fits |
|--------|--------|------|
| `pulse` | heartbeat zoom-throb on each beat | Chorus / beat cuts |
| `shake` | fast positional jitter | Build-up |
| `bounce` | vertical bob on the beat | high-energy |
| `flash` | brightness pulse on the beat | accents |
| `zoomout` / `fade` | slow reveal / dissolve | Intro/Outro / Verse |

Default mapping: Chorus→`pulse` (heartbeat), Build-up→`shake`, Verse→`fade`, Intro/Outro→`zoomout`. Beat-reactive
effects also work as a manual `transition:` on any image. Verified on a real song: 103.4 BPM, 6 sections, with
the heartbeat landing on the chorus beats and shake on the build-up.

> **Scale:** contiguous music-sync slots render via a **concat** path — the prepped clips are stream-**copied**
> (no re-encode), so a full song's hundreds of cut-points render in a couple of seconds regardless of count
> (only an *overlapping* manual timeline uses the heavier N-input overlay). The remaining cost is the one-time
> per-clip prep (~0.2–0.9s each), so a very dense `mode: auto` over a long track still spends most of its time
> preparing clips; `mode: bar` keeps that small. (GPU: the analyzer runs on CPU and is fast enough; your NVIDIA
> GPU + `cuda_libs` are detected and reported via `gpu_available` for a future optional neural backend.)

---

## Secrets / optional environment

Public YouTube videos require **no API key and no secrets**. Optional, user-supplied values may be
placed in a `.env` file (which is **gitignored**). Copy the template to get started:

```powershell
Copy-Item .env-example .env
```

| Variable | Purpose |
|----------|---------|
| `YTDL_PROXY` | Optional HTTP/HTTPS/SOCKS proxy URL passed to yt-dlp (e.g. `http://host:port`). |
| `YTDL_COOKIES_FILE` | Optional path to a Netscape-format `cookies.txt` for age/region-gated public videos. |

No secret literals appear anywhere in the source. `.gitignore` excludes `.env`, `cookies.txt`,
`*.key`, `*.pem`, and `downloads/`.

---

## Architecture

```
CLI (argparse)  ──►  YoutubeDownloaderSDK  ──►  services (Video / Audio / Subtitle / Metadata)
                                            └──►  infra (ytdlp_client, ffmpeg)
                                            └──►  shared (gatekeeper → rate_limit → queue, config, version)
```

- The **SDK (`YoutubeDownloaderSDK`) is the single entry point** for all business logic. The CLI
  (and any future GUI/REST surface) imports only the SDK — no business logic lives in `cli/`.
- **Services** subclass a shared `BaseDownloader` so the yt-dlp options builder, output template,
  and FFmpeg wiring are not duplicated.
- **Infra** confines `yt_dlp` to a single wrapper (`ytdlp_client.py`) and locates FFmpeg via
  `imageio-ffmpeg` (`ffmpeg.py`).
- **Shared** routes every YouTube network call through an `ApiGatekeeper` that enforces rate limits,
  retries transient failures with backoff, logs each call, and feeds a `DownloadQueue`.
- **Every source file is ≤ 150 code lines.**

---

## Testing

```powershell
uv run pytest tests/ --cov=src
uv run ruff check src/ tests/
```

Unit tests mock all external boundaries (`yt_dlp.YoutubeDL`, `imageio_ffmpeg.get_ffmpeg_exe`,
`subprocess`) — no network and no real FFmpeg are used. The suite enforces a coverage gate.

---

## Exit codes

Deterministic, matching the constants in [`src/ytdl/cli/main.py`](src/ytdl/cli/main.py):

| Code | Meaning |
|------|---------|
| `0` | Success. |
| `1` | Other / unexpected error. |
| `2` | Invalid/unavailable URL, or argparse/missing-url/missing-`--dir` usage errors. |
| `3` | Network failure after retries. |
| `4` | Unsupported request. |
| `5` | Configuration version mismatch. |
| `6` | Rate limit / quota reached (configured cap or YouTube HTTP 429) — stopped to protect the account. |
| `7` | Playback dependency missing (VLC not installed) — mix / sampler / playlist modes. |
| `8` | Invalid or malformed playlist YAML (`PlaylistError`) — `--playlist-file` only. |

---

## Future / out of scope (v1.00)

The following are **explicitly out of scope for v1.00** and listed here only for direction:

- **Subtitle translation** and multi-language subtitle download.
- **GPU-accelerated transcription** of downloaded audio. If added, it would integrate
  [`youtube-transcript-api`](https://pypi.org/project/youtube-transcript-api/) and, for local Whisper
  transcription, **reference** `C:\25D\GeneralLearning\transcribe-video\cuda_libs` **in place (never
  copied)** by prepending it to `PATH` before importing the CUDA-backed library — exactly the pattern
  used by transcribe-video's `transcribe.py`. This is the only place GPU/CUDA would ever enter the
  project.

  ```python
  # Future-only pattern (NOT used in v1.00):
  import os
  from pathlib import Path
  CUDA_LIBS = Path(r"C:\25D\GeneralLearning\transcribe-video\cuda_libs")
  os.environ["PATH"] = str(CUDA_LIBS) + os.pathsep + os.environ.get("PATH", "")
  ```

> **Removable-drive safety note (for future maintainers):** any future re-consultation of the
> knowledge graph that lives on the **D: USB drive** must first verify `Test-Path D:\` and stop if
> the drive is absent — blind access to a missing removable drive hangs. This is not part of v1.00.

## Known limitations (v1.00)

- When **both** `--video` and `--audio` are requested in the same run, yt-dlp's
  `keepvideo` (required so audio extraction does not delete the merged mp4) also
  leaves the intermediate per-stream files (e.g. `name.f137.mp4`, `name.f251.webm`)
  next to the final `name.mp4` / `name.mp3`. The required outputs are correct; the
  intermediates are harmless leftovers. Automatic cleanup is planned for a future release.
