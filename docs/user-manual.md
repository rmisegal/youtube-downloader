# User Manual — youtube-downloader (Beat-Sync Video Mixer / VJ toolkit)

**Author:** Dr. Yoram Segal — `segal@gal-tech.ai`
**© 2026 Dr. Yoram Segal. All Rights Reserved.**

> This software was created by **Dr. Yoram Segal (`segal@gal-tech.ai`)** for the study and educational use of
> his students. **All rights reserved.** Personal/educational use is permitted; redistribution and
> **commercial use require prior written permission — for commercial usage please contact Dr. Yoram Segal at
> `segal@gal-tech.ai`.** Third-party open-source dependencies remain under their own licenses (see §14).

---

## Table of contents
1. [Short description](#1-short-description)
2. [Command examples](#2-command-examples)
3. [Code objective](#3-code-objective)
4. [15 use cases](#4-15-use-cases)
5. [Long, end-to-end use cases](#5-long-end-to-end-use-cases)
6. [Command-line arguments — reference](#6-command-line-arguments--reference)
7. [Installation (Windows / Linux / macOS) + VLC + GPU](#7-installation)
8. [Tips & creative workflows](#8-tips--creative-workflows)
9. [The audio auto-sync mechanism](#9-the-audio-auto-sync-mechanism)
10. [The transition mechanism (images & videos)](#10-the-transition-mechanism)
11. [The playlist file — every field](#11-the-playlist-file--every-field)
12. [The configuration file — every field](#12-the-configuration-file--every-field)
13. [How to test the code](#13-how-to-test-the-code)
14. [External code, libraries & license agreements](#14-external-code-libraries--license-agreements)
15. [Technical specification](#15-technical-specification)
16. [Troubleshooting, exit codes, FAQ & support](#16-troubleshooting-exit-codes-faq--support)

---

## 1. Short description

`youtube-downloader` is a command-line toolkit that grew from a **YouTube downloader** into a full
**video-mixing / VJ / music-video studio**. From one terminal it can:

* **Download** a YouTube video as **mp4**, extract **mp3 audio**, and/or fetch **subtitles (.srt)** — in any
  combination, with playlist selection and account-friendly rate limiting.
* **Mix** a folder of local clips into a continuous crossfaded show (VJ mode), live in VLC.
* **Sample-preview** a folder (random mid-band crossfades) in one VLC window.
* Run **declarative YAML playlists** that mix **videos and still images** over a **leading soundtrack**, place
  visuals on an **absolute timeline**, and animate images with transitions.
* **Analyze music** (beats / bars / phrases / sections) and **auto-sync** playlist transitions to the song —
  including **beat-reactive effects** (heartbeat pulse, shake, bounce, flash) that move in time with the BPM.

The engine is `yt-dlp` + FFmpeg (`imageio-ffmpeg`) + VLC (`python-vlc`) + `librosa` for music analysis.

### Key benefit — it runs **without any LLM**, so there are **no token costs**
The entire pipeline (download, mix, analyze, beat-sync, render) is **classic deterministic software** — it does
**not** call any AI model and **does not cost a single token**. You drive it with plain terminal commands and a
small YAML file. That makes it **free to run**, **fast**, **offline**, and **repeatable**.

If you *prefer* a more intuitive, conversational way to drive it, you **can optionally** put a Large Language
Model (LLM) *in front of it* — wire this tool as an agent **skill/tool** so you describe the video you want in
**free natural language** and the LLM writes the playlist / runs the commands for you (see the tips in §8). That
convenience is **opt-in and costs money** (LLM provider tokens) — or it can be **free** if you run a **local
LLM** (e.g. via Ollama) on a strong PC. **The tool itself never requires an LLM.**

> **What this tool is — and is NOT.** This is strictly a **video / audio / image *editor* and *mixer***: it
> sets the **order** of your media, the **transitions** between them, and the **synchronisation** to the music.
> **It does NOT *generate* fake images or fake video** — it does not create or synthesise any visual content. It
> only **combines media you already have** (your clips, photos, recordings, downloads) into **one movie**. Any
> AI-generated media is something *you* create with other tools beforehand and simply feed in as input files.

---

## 2. Command examples

```powershell
# --- Downloading ---
uv run python -m ytdl "https://youtu.be/VIDEO" --video                 # mp4 only
uv run python -m ytdl "https://youtu.be/VIDEO" --audio                 # mp3 only
uv run python -m ytdl "https://youtu.be/VIDEO" --video --audio --subs  # all three
uv run python -m ytdl "https://youtu.be/VIDEO" --video --resolution 720 -o "C:\out"
uv run python -m ytdl "https://youtu.be/LIST"  --audio --playlist-items "1,3,5"

# --- Mixing / VJ ---
uv run python -m ytdl --mix --dir "C:\clips" --mode option1 --crossfade-time 4
uv run python -m ytdl --sample-play --dir "C:\clips" --play-for-sec 8

# --- Declarative playlists (videos + images + leading audio) ---
uv run python -m ytdl --playlist-file "C:\lists\show.yaml"

# --- Music analysis (beat-sync) ---
uv run python -m ytdl --analyze "C:\music\song.mp3" --fps 30 -o beats.json
uv run python -m ytdl --analyze "C:\music\song.mp3" --levels beat,bar --format csv -o beats.csv

# --- Help / info ---
uv run python -m ytdl --command       # run-command cheat-sheet with examples
uv run python -m ytdl --version        # code + config version
```

---

## 3. Code objective

The objective is to give a creator a **single, scriptable, account-safe tool** that turns raw media (YouTube
videos, local clips, still images, a music track) into a finished, **music-synchronised** video — without a
manual NLE. Design objectives:

* **One entry point (SDK-first).** All logic lives behind `YoutubeDownloaderSDK`; the CLI only parses flags
  and maps errors to exit codes. A future GUI/REST layer can reuse the same SDK.
* **Reuse, not duplication.** An image, a video, and a sampled clip all become the same `MixSegment` and flow
  through the same prep → render-one-file → one-VLC pipeline.
* **Config-driven & versioned.** No magic numbers in code; everything tunable lives in `config/setup.json`
  (and `config/rate_limits.json`), each carrying a `version`.
* **Account safety.** Every YouTube request passes a rate-limit gatekeeper (per-minute/hour/day/month quotas)
  so you do not get throttled or blocked.
* **Deterministic & testable.** Small files (≤150 code lines), ≥85 % test coverage, zero-lint, deterministic
  exit codes.

---

## 4. 15 use cases

1. **DJ / VJ video-art mix** — point `--mix` at a folder of loops; get an endless crossfaded visual set in VLC.
2. **Convert a presentation to a movie** — export slides as images, list them in a playlist over a narration
   track; each slide appears on the timeline (or on the beat).
3. **Create a music video clip** — a folder of images/short clips + one song + `sync: {enabled: true}` → a
   beat-cut clip where visuals change on the music.
4. **Turn a lecture into an engaging video** — use **your own voice recording as the leading audio**, and let
   slides/images/B-roll appear in sync above it.
5. **Mix a music playlist** — several songs as members with crossfades, optionally a leading master track.
6. **Save a video from YouTube** — the original downloader: `--video` / `--audio` / `--subs`.
7. **Beat-synced photo slideshow** — 10 holiday photos + a song, `mode: auto` → heartbeat pulse on the chorus,
   slow zoom on the intro.
8. **Karaoke / lyric backdrop** — a subtitle (lyrics) leading layout over a looping visual.
9. **Build a VJ loop library** — `--sample-play` to audition a folder fast, keep the good clips.
10. **Trailer / teaser** — pick in/out points per member (`start_time` / `play_time`), crossfade into a punchy
    montage.
11. **Podcast-to-video** — audio leading track + a single static image or slow Ken-Burns photos.
12. **Social reels** — short vertical images synced to a trending beat (set `render` to a vertical canvas).
13. **Event recap** — mix event clips + photos over the event's theme song.
14. **Export cut-points for an NLE** — `--analyze … -o beats.json` and import markers into Premiere/After
    Effects.
15. **Automated AI music video** — generate images with an LLM, generate a song with an AI tool, drop both in
    a folder, and let the code build a BPM-synced video (see §8).

---

## 5. Long, end-to-end use cases

> **How to use these examples.** Each block below is a **playlist file**. Save it as a plain-text file with a
> **`.yaml`** (or `.yml`) extension — for example with Notepad, VS Code, or `notepad C:\lists\show.yaml` — using
> the file name given under each heading, then run it with `--playlist-file <path>`. The folder for the file is
> up to you; in these examples we use `C:\lists\`. Adjust the `source_folder`, `leading.file`, and member file
> names to your own paths.

### 5.1 Full mix (no leading track)
A continuous crossfaded montage where each member contributes both picture and sound.
**Save as `C:\lists\show.yaml`:**
```yaml
version: "1.05"
metadata:
  source_folder: 'C:\clips'
  output: { display: true, save: true }
  mix:    { video: true, audio: true }
  leading:{ kind: none }
  loop: true
members:
  - { id: 1, file: a.mp4, start_time: 5,  play_time: 20 }
  - { id: 2, file: b.mp4, start_time: 0,  play_time: 25 }
  - { id: 3, file: c.mp4, play_time: 18 }
```
**Run it:**
```powershell
uv run python -m ytdl --playlist-file "C:\lists\show.yaml"
```
→ one VLC window, total length ≈ Σ play_time − crossfades (and, because `save: true`, one mp4 in `target_folder`).

### 5.2 Audio leading track **with beat-sync** (the music-video case)
The song is the master; photos/clips are auto-placed on its beats and the transition is fitted to the music.
**Save as `C:\lists\music-video.yaml`:**
```yaml
version: "1.05"
metadata:
  source_folder: 'C:\photos'
  output:  { display: true }
  mix:     { video: true, audio: false }     # members contribute picture only
  leading: { kind: audio, file: 'C:\music\song.mp3' }
  sync:    { enabled: true, mode: auto }      # context-aware planner
members:
  - { id: 1, type: image, file: 1.jpg }       # the planner assigns at/until + effect
  - { id: 2, type: image, file: 2.jpg }
  - { id: 3, type: image, file: 3.jpg }
```
**Run it:**
```powershell
uv run python -m ytdl --playlist-file "C:\lists\music-video.yaml"
```
The song is analyzed (beats/bars/phrases/sections); images cycle across the cut-points; the **chorus gets a
heartbeat `pulse`, the build-up gets `shake`, the intro a slow `zoomout`**. If the visuals are shorter than the
song it **fades out**; if longer, the song **crossfade-loops**.

### 5.3 Video leading track
A master video drives the picture **and** length; members supply the audio mix (its own audio is dropped).
**Save as `C:\lists\video-leading.yaml`:**
```yaml
version: "1.05"
metadata:
  output:  { display: true }
  mix:     { video: false, audio: true }
  leading: { kind: video, file: 'C:\clips\master.mp4' }
members:
  - { id: 1, file: song1.mp3, play_time: 60 }
  - { id: 2, file: song2.mp3, play_time: 60 }
```
**Run it:**
```powershell
uv run python -m ytdl --playlist-file "C:\lists\video-leading.yaml"
```

### 5.4 Subtitle leading layout
Members carry per-member subtitle requests; enable the subtitle mix stream so a lyrics/caption track rides over
the visuals.
**Save as `C:\lists\lyrics.yaml`:**
```yaml
version: "1.05"
metadata:
  output: { display: true }
  mix:    { video: true, audio: true, subtitle: true }   # subtitle stream ON
members:
  - { id: 1, file: scene.mp4, subtitle: "C:\subs\lyrics.srt" }
```
**Run it:**
```powershell
uv run python -m ytdl --playlist-file "C:\lists\lyrics.yaml"
```
(If `mix.subtitle` is **off**, per-member subtitle requests are honestly dropped.)

### 5.5 Maximum-coverage workflow — from a YouTube search to a finished mix
This exercises most of the toolkit. (Searching/collecting are manual steps; the code does the heavy lifting.)

1. **Find material.** Search YouTube for your topic (e.g. "city timelapse 4k"). Copy a few video URLs.
2. **Hand the URLs to the code.** Download each as mp4 into one folder:
   ```powershell
   uv run python -m ytdl "https://youtu.be/AAA" --video --resolution 1080 -o "C:\build\clips"
   uv run python -m ytdl "https://youtu.be/BBB" --video --resolution 1080 -o "C:\build\clips"
   ```
3. **Fast-scan the folder** to audition what you grabbed and discard the weak clips:
   ```powershell
   uv run python -m ytdl --sample-play --dir "C:\build\clips" --play-for-sec 8
   ```
4. **Pick the leading audio.** Download a song (or use your own), e.g.:
   ```powershell
   uv run python -m ytdl "https://youtu.be/SONG" --audio -o "C:\build\music"
   ```
   Inspect its rhythm/structure:
   ```powershell
   uv run python -m ytdl --analyze "C:\build\music\SONG.mp3" --fps 30 -o "C:\build\beats.json"
   ```
5. **Collect the visuals** (the kept clips + any photos) into `C:\build\clips`.
6. **Write the playlist** (`C:\build\mix.yaml`) with the song as the leading audio and `sync.enabled: true`,
   then **run the mix**:
   ```powershell
   uv run python -m ytdl --playlist-file "C:\build\mix.yaml"
   ```
   One VLC window opens, auto-plays, and is replayable: the clips/photos are cut to the song's beats with
   effects fitted to each section. Add `output: { save: true }` to also write the file.

---

## 6. Command-line arguments — reference

Run as `uv run python -m ytdl [URL] [flags]`. Exactly one *mode* is chosen: a URL (download), `--mix`,
`--sample-play`, `--playlist-file`, `--analyze`, `--version`, or `--command`.

| Argument | Value | What it does | When to use |
|----------|-------|--------------|-------------|
| `URL` | positional | The YouTube video/playlist URL to download. | Downloading from YouTube. |
| `--video` | flag | Download best-quality **mp4**. | Save the picture. |
| `--audio` | flag | Extract **mp3** audio. | Save just the sound / grab a leading track. |
| `--subs` | flag | Download subtitles as **.srt**. | Captions / lyrics. |
| `-o, --output-dir` | path | Output folder (download) **or output file** (`--analyze`). Created if missing. | Choose where results go. |
| `-n, --name` | text | Output base file name (no extension). | Rename instead of using the title. |
| `--resolution` | int | Max video height (e.g. `1080`, `720`). | Cap size/bandwidth. |
| `--sub-lang` | code | Subtitle language (default `en`). | Non-English captions. |
| `--no-playlist` | flag | For a list URL, grab only the single video. | Skip the rest of a list. |
| `--playlist-items` | e.g. `1,3,5` / `1-5` | Download only these list items (skips the prompt). | Batch-select from a list. |
| `--mix` | flag | Live VJ mixer over `--dir` instead of downloading. | Endless crossfaded visuals. |
| `--dir` | path | Folder of local assets (required with `--mix` / `--sample-play`). | Source for mix/sample. |
| `--mode` | `option1`/`option2` | Engine: option1 (FFmpeg→VLC, true crossfade) or option2 (dual-libVLC). Default `option2`. | option1 for clean crossfades. |
| `--selection` | `random`/`manual` | Track order: shuffle or a numbered picker. Default `random`. | Curate vs auto. |
| `--crossfade-time` | int | Crossfade overlap seconds (default `3`). | Faster/slower blends. |
| `--source-mix-time` | float | Seconds into a clip where the crossfade begins. | Trim tails. |
| `--target-start-time` | float | In-point (seconds) where the next clip starts. | Skip intros. |
| `--sample-play` | flag | Audition `--dir`: crossfade random mid-band samples of each clip. | Fast folder triage. |
| `--play-for-sec` | float | Seconds to play each clip before the crossfade. | Sampler/mix pacing. |
| `--playlist-file` | path | Run a declarative **YAML playlist**. | The full mixer (images/videos/sync). |
| `--analyze` | path | Analyze an audio file's beats/bars/phrases/sections, then exit. | Export cut-points / inspect a song. |
| `--fps` | float | Target FPS for analysis frame indices (default from config). | Match your project FPS. |
| `--levels` | csv | Tiers to extract: `beat,bar,phrase,section` (default all). | Limit the JSON. |
| `--format` | `json`/`csv` | `--analyze` output format written to `-o`. | CSV for spreadsheets/NLEs. |
| `-v, --verbose` | flag | Show INFO progress on the console (default: errors only). | Debugging. |
| `--version` | flag | Print code + config version and exit. | Support / bug reports. |
| `-command, --command` | flag | Print the run-command cheat-sheet (examples) and exit. | Quick reference. |

---

## 7. Installation

### 7.1 Prerequisites
* **Python ≥ 3.10** (3.12 recommended).
* **[uv](https://docs.astral.sh/uv/)** — the package/run manager used throughout (never `pip`).
* **VLC media player** — required only for *display/stream* (mix/sample/playlist playback), not for downloading
  or analysis.
* **FFmpeg** — **bundled automatically** via the `imageio-ffmpeg` Python package; you do **not** install it
  separately.

### 7.2 Install `uv`
```powershell
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 7.3 Clone & set up (all platforms)
```bash
git clone https://github.com/rmisegal/youtube-downloader.git
cd youtube-downloader
uv sync           # creates the venv and installs all dependencies (incl. librosa)
```
Run anything with `uv run python -m ytdl …`.

### 7.4 Install VLC (for playback only)
* **Windows:** download from [videolan.org](https://www.videolan.org/) and install (the tool auto-detects the
  default install path).
* **Linux:** `sudo apt install vlc` (Debian/Ubuntu) or your distro's package.
* **macOS:** `brew install --cask vlc` or download the `.dmg`.

> The project was written and tested primarily on **Windows PowerShell**. The Python code is cross-platform;
> on Linux/macOS use a normal shell. Some default Windows paths (e.g. VLC auto-detect) differ per OS — set
> `ffmpeg.location`/VLC on PATH if auto-detection fails.

### 7.5 GPU — is it used? Is it mandatory?
**No GPU is required, and none is used for the core pipeline.**

* Downloading, mixing, and rendering are **FFmpeg/CPU**.
* Music analysis uses **librosa, which is CPU-only**. With the built-in FFmpeg-predecode it analyses a 4-minute
  track in well under 10 s on a normal desktop CPU, so a GPU brings **no benefit** here.
* The toolkit **detects** an NVIDIA GPU (and can put the shared CUDA/cuDNN DLLs on `PATH` *in place*) and
  reports `gpu_available` in the analysis metadata. This is **optional** infrastructure reserved for a *future*
  neural beat backend; today the device is honestly reported as **`cpu`**.
* `analysis.use_gpu` in the config accepts `auto` (default) / `on` / `off`. Leave it `auto`; it never forces a
  GPU path that does not exist.

**Bottom line:** GPU is **optional and currently unused** — install nothing extra; the CPU path is the fast
path.

---

## 8. Tips & creative workflows

* **Original music with SUNO AI.** Generate a royalty-free original song with [SUNO](https://suno.com/), save
  the mp3, and use it as your `leading: { kind: audio }` track — then beat-sync your visuals to it (§5.2). This
  keeps you clear of copyright on the soundtrack.
* **AI micro-clips (e.g. nano-banana / image-to-video LLMs).** Generate several short (~8 s) AI video clips,
  drop them in a folder with **one** original music track, and let the mixer stitch + sync them. Short
  AI clips become "members" exactly like any video.
* **AI images synced to music.** Use an LLM image generator to create a themed image set, put them in a folder
  with a song, set `sync: { enabled: true, mode: auto }`, and the code builds **video-art that cuts on the
  beat and pulses with the BPM** — no manual editing.
* **Let an LLM write the playlist.** Ask an LLM (e.g. Gemini/Claude) to generate the **YAML playlist** for you:
  give it your file list + the song and the schema from §11, and paste the result as your `--playlist-file`.
* **Use it as an agent skill / tool — drive everything in free natural language.** Because every capability is
  exposed through one clean entry point (the `YoutubeDownloaderSDK` and the CLI), you can register this tool as
  a **"skill"/tool for an AI agent** (Claude/Gemini/an MCP tool, etc.). The agent then turns a plain-language
  request like *"make me a 30-second beat-synced clip from these 8 photos and this song"* into the right
  playlist + commands and runs them — no terminal knowledge needed. Two cost models: **(a)** a **cloud LLM**
  (you pay your provider's **tokens**), or **(b)** a **local LLM** (e.g. **Ollama** with tool-calling) which is
  **free of token charges** but needs a **strong PC** (a capable GPU/lots of RAM) to run well. Remember: this is
  *optional sugar on top* — the tool itself still works fully **without any LLM and without paying anything**.
* **Pick the right tempo.** Songs around 90–120 BPM give comfortable photo pacing; faster songs produce more
  cuts. Use `--analyze` first to see the BPM and section map before committing.
* **Keep prep fast.** Dense `mode: auto` over a long song prepares one short clip per cut — use `mode: bar` for
  a quicker render, or shorter songs/sections for the full beat-reactive treatment.
* **Vertical/Reels.** Set `render.width`/`render.height` to a portrait canvas (e.g. 720×1280) before rendering.

---

## 9. The audio auto-sync mechanism

**Concept.** Instead of placing visuals by hand, the tool *listens* to the leading song and snaps your cuts to
the music's natural grid. It extracts four hierarchical tiers and then plans cuts from them.

**Analysis tiers (librosa):**
* **Beats & onsets** — individual pulses + transient hits; global BPM.
* **Bars / downbeats** — beats grouped by meter (default 4/4); the downbeat is the strongest-onset beat.
* **Phrases** — 4/8-bar musical "sentences".
* **Sections** — Intro / Verse / Build-up / Chorus / Outro (boundaries from beat-synchronous chroma clustering;
  labels are heuristic).

**Context-Aware Cut Planner (`mode: auto`).** The **section dictates the cut rhythm** (configurable):
Intro/Outro → **phrase** (slow), Verse → **bar** (steady), Build-up/Chorus → **beat** (energetic), plus
optional **phrase-end drum-fill bursts** ("visual punctuation"). You can override with a fixed grid:
`mode: beat | bar | phrase | section`.

**What it can do:**
* Auto-place any number of image/video members on the song's cut-points (members cycle to fill the track).
* **Fit the transition to the sync type** (see §10) — fast effects on energetic beats, slow on phrases.
* Drive **beat-reactive effects** at the exact BPM (pulse/shake/bounce/flash).
* Handle length automatically: visuals shorter than the song → audio fades out; longer → song loops.

**Standalone export.** `--analyze` writes the full cut-point map (with `frame_index = round(t × fps)`) to
JSON/CSV for use in an NLE (Premiere/After Effects markers).

**Performance & device.** Runs on **CPU** (librosa); an FFmpeg-predecode keeps a 4-minute track under ~10 s.

---

## 10. The transition mechanism

Every image member is turned into an animated clip; videos are placed/trimmed. Transitions fall into two
families:

**Static transitions** (no music needed): `fade`, `zoomin`, `zoomout`, `panleft`/`panright`/`panup`/`pandown`
(Ken-Burns pan + `direction`). Every image also gets a short edge fade so overlapping slots blend.

**Beat-reactive effects** (oscillate at the analyzed **BPM**):

| Effect | Motion | Best on |
|--------|--------|---------|
| `pulse` | heartbeat zoom-throb on each beat | Chorus / beat cuts |
| `shake` | fast positional jitter | Build-up |
| `bounce`| vertical bob on the beat | high-energy |
| `flash` | brightness pulse on the beat | accents |

**Auto-selection & music dependency.**
* In a **manual** playlist you set `transition:` per image (or `random`, the default, which picks a *static*
  transition — beat effects need a tempo, so they are opt-in).
* In a **music-synced** playlist the planner **chooses the transition for you** at each cut, fitting it to that
  cut's musical role via two config maps:
  * `analysis.tier_transitions` — by tier (beat→pulse, bar→fade, phrase→zoomout, section→panright).
  * `analysis.section_transitions` — by section label, **overrides** the tier map (Chorus→pulse,
    Build-up→shake, Verse→fade, Intro/Outro→zoomout).
* The chosen BPM is attached to each placed clip so beat-reactive effects throb **in time with the song**.

**Placement / overlap.** Members carry an absolute timeline position (`at` … `until`). A later member overlays
an earlier one (so an image can sit on top of a running video). When slots are **contiguous** (the sync case)
the renderer **concatenates** the clips (video stream-copied — fast at any count); only **overlapping** manual
timelines use the heavier overlay compositor.

---

## 11. The playlist file — every field

A playlist is a YAML file passed with `--playlist-file`. Top level: `version`, `metadata`, `members`.

```yaml
version: "1.05"            # REQUIRED. Schema version (supported: 1.03–1.05).
metadata:
  source_folder: 'C:\media'   # base folder for bare member file names. Use it so members can be just "a.jpg".
  target_folder: 'C:\out'     # where a `save` render is written.
  output:                     # routing — any combination:
    display: true             #   live VLC playback (one window, auto-plays, replayable).
    save:    false            #   render ONE file into target_folder (skipped for image/timeline playlists today).
    stream:  false            #   local VLC loopback broadcast (no external push).
  mix:                        # which streams the MEMBERS contribute:
    video:    true            #   members provide picture.
    audio:    false           #   members provide sound (turn OFF when a leading audio is the only sound).
    subtitle: false           #   honour per-member subtitle requests.
  leading:                    # the MASTER track:
    kind: audio               #   none | video | audio.
    file: 'C:\media\song.mp3' #   the master file (empty when kind=none).
  sync:                       # music auto-sync (beat-sync):
    enabled: true             #   turn auto-placement ON (requires kind=audio).
    mode: auto                #   auto | beat | bar | phrase | section.
  loop: true                  # repeat the show while displaying.
members:
  - id: 1                     # REQUIRED, unique; members are ordered by id.
    file: clip.mp4            # REQUIRED. Bare name (joined to source_folder) or absolute path/URL.
    type: video               # video | image (default video).
    start_time: 25            # in-point seconds (video source -ss).
    play_time: 30             # seconds to play (video). For an IMAGE, duration = until - at.
    playback_speed: 1.0       # speed multiplier (video).
    resolution: max           # "max" or "WxH"/height.
    subtitle: "C:\s\a.srt"    # null/false = off, true = embedded, "<file>" = insert.
    effect: fade              # legacy mix effect name.
    at: 10                    # ABSOLUTE timeline start (seconds). Set by the planner in sync mode.
    until: 18                 # ABSOLUTE timeline end (seconds) — images.
    transition: random        # image animation: fade|zoomin|zoomout|pan*|pulse|shake|bounce|flash|random.
    direction: left           # pan direction: left|right|up|down.
```

**When/why to use each block:**
* **`source_folder`** — keeps member entries short and portable; without it, give absolute paths.
* **`output`** — `display` for previewing, `save` to produce a deliverable, `stream` for a local broadcast.
* **`mix`** — the honest gate: turn `audio: false` when a leading song should be the only sound; turn
  `subtitle: true` only when you actually want captions burned into the mix.
* **`leading`** — `audio` for music videos (song is master), `video` for "drive picture from a master clip,
  take sound from members", `none` for a plain crossfade montage.
* **`sync`** — enable to let the song place your visuals; `mode: auto` for the context-aware feel, a fixed tier
  for predictable pacing.
* **Member `at`/`until`** — set them yourself for a hand-built timeline (e.g. an image over a video at 0:10–0:18);
  leave them out under `sync` and the planner fills them.
* **`transition`/`direction`** — art direction per image; omit for `random`, or pick a beat effect for accents.

> **Validation & errors.** A malformed playlist (bad YAML, missing `version`/`id`/`file`, unknown member file,
> unsupported version) exits with **code 8**. Save of an image/timeline playlist is a current limitation (it is
> skipped with a warning; use `display`).

---

## 12. The configuration file — every field

Two JSON files in `config/`, each versioned. Defaults are sensible; override only what you need.

### 12.1 `config/setup.json`
```jsonc
{
  "version": "1.05",
  "paths":   { "output_dir": "./downloads" },     // default download folder.
  "analysis": {                                    // --- beat-sync engine ---
    "default_fps": 30,                             // FPS for frame indices when --fps is omitted.
    "default_levels": ["beat","bar","phrase","section"], // tiers extracted by default.
    "meter": 4,                                    // beats per bar (4/4). Use 3 for waltz-time.
    "phrase_bars": 8,                              // bars per phrase (4 or 8).
    "sample_rate": 22050,                          // analysis sample rate (Hz) — higher = slower, rarely needed.
    "downbeat_backend": "auto",                    // auto|librosa (madmom sidecar reserved for the future).
    "use_gpu": "auto",                             // auto|on|off — GPU is optional & currently unused (see §7.5).
    "fill_on_phrase_end": true,                    // add drum-fill bursts before phrase boundaries.
    "section_rules": {                             // section -> cut tier (the context-aware strategy):
      "Intro":"phrase","Verse":"bar","Build-up":"beat","Chorus":"beat","Outro":"phrase" },
    "tier_transitions": {                          // cut tier -> transition:
      "beat":"pulse","bar":"fade","phrase":"zoomout","section":"panright" },
    "section_transitions": {                       // section -> transition (OVERRIDES tier_transitions):
      "Intro":"zoomout","Verse":"fade","Build-up":"shake","Chorus":"pulse","Outro":"zoomout" }
  },
  "playback": {                                    // --- mixer / sampler ---
    "default_mode": "option2",                     // option1 (FFmpeg→VLC) | option2 (dual-libVLC).
    "default_selection": "random",                 // random | manual.
    "crossfade_duration_seconds": 3,               // default crossfade overlap.
    "source_mix_time_seconds": null,               // where in a clip the crossfade starts (null = clip end).
    "target_start_time_seconds": 0,                // in-point for the next clip.
    "supported_video_formats": [".mp4",".mkv",".mov",".avi"]
  },
  "network":   { "js_runtime": "auto" },           // JS runtime for yt-dlp signature solving.
  "defaults":  { "resolution": null, "sub_lang": "en", "modes": ["video"] }, // CLI defaults.
  "audio":     { "codec": "mp3", "quality": "192" },   // mp3 extraction settings.
  "subtitles": { "format": "srt", "include_auto": true }, // include auto-generated captions.
  "ffmpeg":    { "location": "auto" },             // "auto" = use the bundled imageio-ffmpeg binary.
  "sample": {                                      // --sample-play behaviour:
    "play_seconds": 10, "mid_band_low": 0.25, "mid_band_high": 0.75, "loop": true },
  "render": {                                      // the output canvas/codec for rendered mixes:
    "width": 1280, "height": 720, "fps": 30,
    "video_preset": "ultrafast", "video_codec": "libx264",
    "audio_codec": "aac", "container": "mp4" },
  "logging": {                                     // rotating logs under logs/:
    "dir": "logs", "app_file": "ytdl.log", "subprocess_file": "ffmpeg.log",
    "max_bytes": 1048576, "console_level": "ERROR" }
}
```
**When/why to change common fields:** set `render.width/height` for portrait/HD; lower `render.video_preset`
(e.g. `medium`) for smaller files; tune `analysis.meter`/`phrase_bars` to the song's time signature; flip
`use_gpu` to `off` to skip GPU detection entirely; edit `tier_transitions`/`section_transitions` to art-direct
the auto-sync look; raise `audio.quality` for better mp3.

### 12.2 `config/rate_limits.json`
Protects your YouTube account by capping request volume.
```jsonc
{
  "version": "1.03",
  "rate_limits": { "services": { "youtube": {
    "requests_per_minute": 10, "requests_per_hour": 200,
    "requests_per_day": 1000, "requests_per_month": 10000,
    "concurrent_max": 1, "burst_size": 5, "burst_window_seconds": 10,
    "retry_after_seconds": 30, "max_retries": 3,
    "download": { "limit_rate": "5M", "throttled_rate": "100K",
      "sleep_requests_seconds": 1.0, "sleep_interval_seconds": 3.0,
      "max_sleep_interval_seconds": 8.0, "concurrent_fragments": 1,
      "retries": 10, "fragment_retries": 10 } } },
    "default": { "requests_per_minute": 30, "concurrent_max": 5,
      "retry_after_seconds": 30, "max_retries": 3 } },
  "queue": { "max_depth": 100, "drain_interval_seconds": 1,
    "timeout_seconds": 300, "overflow_strategy": "reject_oldest" },
  "usage_state_file": "config/.usage_state.json"
}
```
**When/why:** lower the per-minute/hour quotas if you share an IP or hit 429s; raise `limit_rate` for faster
downloads on a strong connection; the persistent `usage_state_file` ledger remembers your usage across runs.
Hitting a quota (or a YouTube HTTP 429) exits with **code 6** — by design, to protect the account.

---

## 13. How to test the code

The project is test-driven; all FFmpeg/VLC/librosa calls are mocked so the suite is fast and offline.

```bash
uv run pytest                                  # run the whole suite
uv run pytest --cov=src --cov-report=term      # with coverage (gate: ≥ 85 %, fail_under enforced)
uv run pytest tests/unit/services/analysis/    # one area
uv run ruff check src/ tests/                  # zero-lint gate
```

**What you can test:**
* **Unit** — every pure unit: the cut planner, beat-effect filter strings, transition resolution, JSON/CSV
  export & frame-index math, bars/phrases derivation, section labeling, sync placement, config validation,
  playlist parsing, rate-limit accounting, exit-code mapping.
* **Command builders** — the exact FFmpeg argument lists for image prep, the timeline overlay, the concat
  renderer, and the leading-audio trim/fade — asserted without spawning FFmpeg.
* **Integration (manual, real FFmpeg, no GUI)** — render a small playlist to one mp4 and probe its duration
  (the repo's verification scripts do exactly this).
* **File-size guard** — every source file ≤ 150 code lines.

Add a test for any bug before fixing it (TDD): write a failing unit, fix, watch it pass, keep coverage ≥ 85 %.

---

## 14. External code, libraries & license agreements

This project stands on third-party open-source software. Each remains under **its own license**; the
"All Rights Reserved" terms of this project (§ header) apply only to Dr. Segal's original code. If you ever
distribute a build, you must comply with each component's terms — note especially the **(L)GPL** components
**FFmpeg** and **VLC**.

| Component | Role | License (verify before redistribution) |
|-----------|------|------------------------------------------|
| **yt-dlp** | YouTube download engine | The Unlicense (public domain dedication) |
| **FFmpeg** (binary via `imageio-ffmpeg`) | decode/encode/filters | **LGPL-2.1+** (some builds GPL-2.0+) — © FFmpeg authors |
| **imageio-ffmpeg** | ships/locates the FFmpeg binary | BSD-2-Clause |
| **VLC media player** (VideoLAN) | playback engine | **GPL-2.0+ / LGPL-2.1+** |
| **python-vlc** | Python bindings to libVLC | LGPL-2.1-or-later |
| **librosa** | music/audio analysis | ISC |
| **NumPy** | numerics | BSD-3-Clause |
| **SciPy** | signal processing | BSD-3-Clause |
| **SoundFile** (libsndfile) | audio I/O | BSD-3-Clause (libsndfile: LGPL-2.1+) |
| **Numba** / **llvmlite** | JIT acceleration in librosa | BSD-2-Clause |
| **audioread / pooch / joblib / scikit-learn** | librosa runtime deps | BSD / ISC |
| **PyYAML** | playlist parsing | MIT |
| **pytest** / **pytest-cov** | test framework/coverage | MIT |
| **ruff** | linter | MIT |
| **uv** (Astral) | package/run manager | MIT / Apache-2.0 |
| **madmom** *(optional, not installed)* | neural downbeats (future sidecar) | BSD-2-Clause; bundled models are academic/non-commercial — check before any commercial use |

**Action taken:** all components are credited here and in the repository `LICENSE`. Users intending
**commercial** distribution must (a) obtain Dr. Segal's written permission for this project's code, **and**
(b) honour the FFmpeg/VLC (L)GPL and any model-license restrictions of the components above.

> Content rights: downloading copyrighted YouTube material and using copyrighted music may be subject to the
> rights of their owners and YouTube's Terms of Service. Use your own/licensed/royalty-free media (see the SUNO
> tip in §8).

---

## 15. Technical specification

**Language / runtime.** Python ≥ 3.10 (3.12 tested), managed by `uv`. Windows-PowerShell-first, cross-platform
code.

**Architecture (SDK-first, layered).**
```
cli/         argument parsing (args.py, argdefs.py) + dispatch (main.py) + handlers (run.py) + exit codes
  └─ calls ─► sdk/   YoutubeDownloaderSDK  (the ONLY public surface) + wiring (dependency injection)
                 └─ services/   download_op, mixer/ (Sampler, SamplePrep, MixSegment),
                                playlist/ (loader, model, runner, sync), analysis/ (analyzer, beats,
                                grid, structure, cut_planner, export, gpu, audio_io)
                 └─ infra/      ffmpeg locator, playback/ (renderer, timeline, concat, transitions,
                                beat_effects, engines, sample_stream), ytdlp_client
                 └─ shared/     ConfigManager, errors, version, logging
```
**Key design rules (enforced):** one SDK entry point; **every file ≤ 150 code lines**; **uv only** (never
`pip`); **ruff** zero-violations; **TDD** with **≥ 85 %** coverage (`fail_under`); config-driven (no magic
numbers); versioned config & playlist schema; secrets via env (none required).

**The pipeline (one mental model).** Every visual — a sampled clip, a video member, or an animated image —
becomes a uniform **`MixSegment`**, is prepped to a normalized 720p `.ts` by **`SamplePrep`** (synthesising
silent audio when needed), and is then either xfade-stitched, overlaid on an absolute timeline, or
**concatenated** — producing **one mp4** opened in **one VLC** (auto-plays, replayable). The leading audio is
trimmed/faded/looped to fit.

**Beat-sync pipeline.** `audio_io` decodes to WAV via the bundled FFmpeg (fast) → librosa beats/onsets/tempo →
`grid` bars/phrases → `structure` sections → `cut_planner` (context-aware) → `sync.place_on_cuts` assigns
`at/until` + a tier/section-fitted transition + BPM → the concat/timeline renderer.

**Media stack.** yt-dlp (download) · FFmpeg via imageio-ffmpeg (transcode/filters: `xfade`, `zoompan`, `fade`,
`overlay`, `acrossfade`, `eq`, concat demuxer) · python-vlc + VLC (playback) · librosa (analysis).

**Determinism & safety.** Deterministic exit codes (§16); a persistent rate-limit ledger; subprocesses spawned
with `-nostdin` + `stdin=DEVNULL` (no console-stdin hangs) and per-clip timeouts; rotating size-capped logs
under `logs/`.

**Performance.** Analysis < ~10 s for a 4-minute track (CPU). Music-sync render is **stream-copy concat** →
roughly constant in cut count; cost is the one-time per-clip prep.

**Versioning.** Code `__version__` and config/playlist `version` are validated on load; unsupported config
version → exit **5**.

---

## 16. Troubleshooting, exit codes, FAQ & support

### Exit codes
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Generic/unexpected error |
| 2 | Invalid URL **or** usage error (missing URL/dir) |
| 3 | Network failure after retries |
| 4 | Unsupported request (yt-dlp can't handle it) |
| 5 | Config version mismatch |
| 6 | Rate limit / quota hit or YouTube HTTP 429 (account protection) |
| 7 | Playback dependency missing (install **VLC**) |
| 8 | Invalid/malformed playlist YAML |
| 9 | Audio analysis failed (decode/empty/no beats) |

### Troubleshooting
* **"Missing playback dependency" (code 7)** — install VLC (§7.4); it's only needed for display/stream.
* **Playlist won't load (code 8)** — check `version`, every member has `id` + `file`, and files exist; on the
  removable `P:`/`D:`/`H:` drives, make sure the drive is connected.
* **Analysis failed (code 9)** — the audio file is unreadable/empty, or in a format FFmpeg can't decode; try
  re-saving as `.wav`/`.mp3`.
* **Rate limited (code 6)** — wait, or lower the quotas in `rate_limits.json`. This is intentional protection.
* **A sync render is slow** — it's preparing one clip per cut; use `mode: bar` or a shorter song (§8).
* **Nothing plays / black VLC** — ensure VLC is installed and on PATH; check `logs/ffmpeg.log`.

### FAQ
* **Do I need FFmpeg?** No — it's bundled via `imageio-ffmpeg`.
* **Do I need a GPU?** No — the pipeline is CPU and fast (§7.5).
* **Can I use my own song/voice?** Yes — that's the recommended path (and avoids copyright). Use SUNO for
  original music (§8).
* **Where do logs go?** `logs/ytdl.log` and `logs/ffmpeg.log` (rotating).
* **How do I see all commands?** `uv run python -m ytdl --command`.

### Support & licensing
**Author / contact:** **Dr. Yoram Segal — `segal@gal-tech.ai`.**
**© 2026 Dr. Yoram Segal. All Rights Reserved.** For **commercial usage, licensing, or permissions, contact
Dr. Yoram Segal at `segal@gal-tech.ai`.** See [`LICENSE`](../LICENSE) for the full declaration.
