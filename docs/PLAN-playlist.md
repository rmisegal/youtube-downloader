# Implementation Plan — Sampler, Per-Clip Duration & YAML Playlist

**PRD Source:** `docs/PRD-playlist.md`
**Plan Version:** 1.01
**Created:** 2026-06-20
**Owner:** rmisegal@gmail.com
**Execution Mode:** Interactive (executing agents may pause for clarification)

---

## 1. Executive Summary

Extend the v1.02 Video Mixer with three features: a **`--sample-play`** sampler (random mid-band preview of each
clip, looping), a **`--play-for-sec`** per-clip duration, and a declarative **`--playlist-file` YAML** that can
**display** (VLC), **save** (render the whole mix to one file via FFmpeg), and/or **stream** (local VLC loopback).
A shared **`MixSegment`** model gives every feature per-clip timing; new code reuses the existing engines, locators,
and config, and is built SDK-first under all 14 `/glb-quality-code-guidlines` rules. Target version **1.03**.

---

## 2. Scope & Success Criteria

### In scope (PRD §1.3, §3–§6)
- `--sample-play --dir` → random mid-band 10s sample of each clip, crossfading, looping the folder.
- `--play-for-sec N` → each clip plays N seconds before the crossfade.
- `--playlist-file <yaml>` → play and/or render one combined file per YAML metadata (mix toggles, leading track, loop, summary).
- `MixSegment` model; segment-aware engines + `MixRenderer` (save).

### Out of scope (PRD §1.4, §12)
- GUI playlist editor; external RTMP/Twitch/YouTube push (stream = local VLC loopback only).
- Per-pixel video alpha; subtitle styling/positioning; hardware-accel tuning.

### Success metrics (PRD §1.3)
- S1 sampler loops random mid-band samples with crossfades; S2 `--play-for-sec` controls duration;
  S3 YAML plays/renders per metadata; S4 passes the full 14-rule audit (§10).

---

## 3. Assumptions, Constraints, Risks

| ID | Type | Statement | Source | Mitigation |
|----|------|-----------|--------|------------|
| A1 | Assumption | A member `file` may be a YouTube URL; downloaded rate-limited then used as a segment. | §7 | Route via existing `SDK.download`/`ApiGatekeeper`. |
| C1 | Constraint | Every Python file ≤150 code lines. | §7, R8 | Split into segment/sampler/model/loader/summary/renderer. |
| C2 | Constraint | uv only; `pyyaml` added via uv. | §10, R14 | Phase 2 gate scans toolchain. |
| C3 | Constraint | stream = local VLC loopback only (no external endpoint). | §1.4 | Reuse Option-1 `vlc -`. |
| R1 | Risk | Continuous N-clip `xfade` render is complex (offsets/normalization). | §12 | Build display first, then save; renderer normalizes scale/fps/setsar before xfade. |
| R2 | Risk | Leading-track compositing (mute leading-video audio; video-source-as-audio-only) is intricate. | §6 | Explicit `-an`/`-vn`/`-map` directives; unit-test argv. |
| R3 | Risk | Per-segment speed/resolution interact with `xfade` (inputs must share size/SAR/fps). | §12 | Normalize inputs before xfade. |
| R4 | Risk | Additive engine changes could break v1.02 tests. | §2 | New segment-aware entry points beside existing ones; full suite gate. |

---

## 4. Quality Gate Anchors (glb-quality-code-guidlines)

| # | Rule | Primary Anchor Phase |
|---|------|----------------------|
| 1 | SDK Architecture | Phase 4, 6, 7 |
| 2 | OOP / No Duplication | Phase 4, 5, Review |
| 3 | API Gatekeeper | Phase 4 (member-URL reuse) |
| 4 | Rate-Limit Config | Phase 3 (reuse) |
| 5 | Queue Management | Phase 4 (reuse) |
| 6 | Version Control | Phase 2 |
| 7 | TDD | Phases 3–7, 8 |
| 8 | File Size ≤150 | Phases 2–7 |
| 9 | Coverage ≥85% | Phase 8 |
| 10 | Ruff | Phases 2–7 |
| 11 | No Hardcoded | Phase 3, Review |
| 12 | Config Architecture | Phase 3 |
| 13 | Secrets | Phase 9 |
| 14 | uv | Phase 2 |

> **Standing gate (Phases 2–7):** `uv run ruff check src/ tests/` = 0; file-size ≤150; tests-first; v1.02 suite stays green.

---

## 5. Phase Plan

### Phase 1 — Planning & Discovery
- **Objective:** Lock the requirements inventory + reuse map before code. **Refs:** §1–§13. **Rules:** none.
- Steps: 1.1 Confirm inventory R1–R54 (§9). 1.2 Confirm reuse (`PlaylistEngine.scan`, `FfmpegLocator`,
  `probe_duration`, `VlcLocator`, engines, `shared/selection`, `ApiGatekeeper`). 1.3 Confirm Open Questions empty (§8).
- **Gate:** [ ] every PRD demand has an inventory ID; [ ] 14-rule anchors reviewed; [ ] n/a automated.

### Phase 2 — Initialization (deps, version, structure) — Rules 6, 8, 10, 14
- **Refs:** §7, §8.2, §10. **Inventory:** R35–R37 (skeleton), R44, R47.
- Steps: 2.1 `uv add pyyaml`; commit `uv.lock`. 2.2 `version.py`→`1.03`; `setup.json`+`rate_limits.json` `version`→`1.03`;
  `ConfigManager.SUPPORTED_CONFIG_VERSIONS` += `"1.03"`. 2.3 Create skeletons: `services/mixer/{segment,sampler}.py`,
  `services/playlist/{__init__,model,loader,summary}.py`, `infra/playback/renderer.py` + mirrored test dirs.
- **Gate:** [ ] Func: `uv sync` ok; `import yaml` works. [ ] Quality: `uv.lock` present, no requirements.txt (R14);
  versions 1.03 (R6); files ≤150 (R8); ruff clean (R10). [ ] Automated: `uv run ruff check src/`; uv-toolchain scan.

### Phase 3 — Configuration — Rules 6, 7, 11, 12
- **Refs:** §8. **Inventory:** R42, R43, R44, R45.
- Steps (TDD): 3.1 RED tests for new config reads (`sample.*`, `render.*` defaults; version 1.03 validates).
  3.2 Add `setup.json` `sample` block {play_seconds 10, mid_band_low 0.25, mid_band_high 0.75, loop true} and
  `render` block {video_codec, audio_codec, container "mp4"}. 3.3 Add constants (sample/render/effect/output names) to `constants.py`.
- **Gate:** [ ] Func: configs load; defaults returned; 1.03 validates. [ ] Quality: no hardcoded tunables (R11);
  config hierarchy (R12); versioned (R6). [ ] Automated: `uv run pytest tests/unit/shared/test_config.py`.

### Phase 4 — Architecture & Shared Infrastructure — Rules 1, 2, 3, 5, 7, 8, 10
- **Refs:** §2, §6, §9. **Inventory:** R26, R27, R28, R34, R37, R46, R40.
- Steps (TDD): 4.1 `services/mixer/segment.py` `MixSegment` dataclass (R26). 4.2 `shared/errors.py`
  `PlaylistError` (R46). 4.3 Extend `Option1Engine`/`Option2Engine` (+`StreamServer`/`LibVlcPlayerMatrix`) with
  **additive** segment-aware entry points consuming `list[MixSegment]` (per-clip `-ss`/`-t`, cumulative xfade
  offset, `setpts`/`atempo`/`scale`) — keep v1.02 tests green (R27, R28). 4.4 `infra/playback/renderer.py`
  `MixRenderer` (continuous FFmpeg graph; leading-video `-an`/leading-audio `-vn`; normalize scale/fps/setsar;
  codecs from `render` config; subprocess injected) (R29–R34). Member-URL injection reuses `ApiGatekeeper` (R3,R5,R40).
- **Gate:** [ ] Func: MixRenderer argv has correct offsets/`-ss`/`-t`/codecs; leading variants emit `-an`/`-vn`;
  segment engines drive per-clip timing. [ ] Quality: no dup (R2); engines reachable via SDK only (R1); files ≤150 (R8);
  ruff (R10); tests-first (R7); v1.02 suite green (R28). [ ] Automated: `uv run pytest tests/unit/infra tests/unit/services/test_segment*`.

### Phase 5 — Domain Implementation (Sampler, Playlist model/loader/summary) — Rules 2, 7, 8, 10
- **Refs:** §3, §5, §6. **Inventory:** R3–R8, R12–R19, R25, R30, R31, R36.
- Steps (TDD): 5.1 `services/mixer/sampler.py` `Sampler` — `probe_duration` + random mid-band start (injectable RNG,
  config band), `play_seconds`/`--play-for-sec`, loop → `list[MixSegment]` (R3–R8). 5.2 `services/playlist/model.py`
  dataclasses (Playlist/Metadata/Output/Mix/Leading/Member) (R36). 5.3 `services/playlist/loader.py` YAML→model +
  validation → `PlaylistError`; order by `id`; resolve paths rel→`source_folder`; build `MixSegment`s (R12–R15).
  Also **validate the playlist's `version` field** against supported values → `PlaylistError`/exit 8 (R55), and
  **validate each member file exists** with the source-folder + **removable-drive (`D:`/`H:`) guard** →
  `PlaylistError`/exit 2 (R56).
  5.4 mix toggles gate streams; leading-kind selection (video mutes leading audio; audio uses only sound even from a
  video file) (R16–R19, R30, R31). 5.5 `services/playlist/summary.py` compute total length/size/resolution/members;
  write back (R25).
- **Gate:** [ ] Func: malformed YAML → `PlaylistError`; **unsupported playlist `version` → exit 8 (R55)**;
  **missing member file / unmounted drive → exit 2 (R56)**; sampler deterministic under seeded RNG; toggles/leading honored;
  summary computed. [ ] Quality: reuse `selection`/`scan`, no dup (R2); files ≤150 (R8); ruff (R10); tests-first (R7).
  [ ] Automated: `uv run pytest tests/unit/services`.

### Phase 6 — SDK / API Surface — Rules 1, 2, 7
- **Refs:** §7. **Inventory:** R8, R20–R24, R38.
- Steps (TDD): 6.1 `sdk/sdk.py` add `sample_play(directory, *, play_for_sec=None, mode=None)` and
  `play_playlist(yaml_path)`; route output to display/save/stream per metadata (save once even if loop) (R20–R24, R38).
  6.2 `sdk/wiring.py` `build_sampler`/`build_playlist_runner`. 6.3 SDK is the only externally-imported surface (R1).
- **Gate:** [ ] Func: `sample_play` builds segments→engine; `play_playlist` honors output combos + loop + save-once.
  [ ] Quality: all ops via SDK (R1); no dup (R2); tests-first (R7). [ ] Automated: `uv run pytest tests/unit/sdk`.

### Phase 7 — CLI / External Interface — Rules 1, 7, 8, 10
- **Refs:** §3.1, §4, §5.1, §9. **Inventory:** R1, R2, R9, R10, R11, R39, R46.
- Steps (TDD): 7.1 `cli/args.py` add `--sample-play`, `--play-for-sec` (float), `--playlist-file`. 7.2 `cli/main.py`
  route: `--sample-play`→`sample_play`, `--playlist-file`→`play_playlist`; map `PlaylistError`→**exit 8**,
  `PlaybackDependencyError`→7, bad dir/file→2 (R1, R46). 7.3 `cli/usage.py` cheat-sheet entries. 7.4 CLI holds no business logic.
- **Gate:** [ ] Func: flags parse; routing correct; exit codes (8/7/2) mapped. [ ] Quality: CLI delegates to SDK (R1);
  files ≤150 (R8); ruff (R10); tests-first (R7). [ ] Automated: `uv run pytest tests/unit/cli`.

### Phase 8 — Testing & Coverage — Rules 7, 9
- **Refs:** §13. **Inventory:** R50, R51, R52.
- Steps: 8.1 conftest fixtures: tmp YAML / in-memory dicts, mock FFmpeg & VLC subprocess, mock `probe_duration`,
  injectable RNG/clock. 8.2 error-path tests (malformed YAML→8; missing dir→2; missing VLC→7). 8.3 raise coverage ≥85%; test files ≤150.
- **Gate:** [ ] Func: full suite green; no real render/playback/network. [ ] Quality: coverage ≥85% (R9);
  happy+error per public method (R7). [ ] Automated: `uv run pytest tests/ --cov=src --cov-report=term-missing`.

### Phase 9 — Security Review — Rule 13
- **Refs:** §10. **Inventory:** R48.
- Steps: 9.1 secret-scan; confirm no secrets in new modules; YAML loader uses `yaml.safe_load` (no arbitrary object
  construction). 9.2 confirm `.gitignore`/`.env-example` unchanged-and-sufficient.
- **Gate:** [ ] Func: `safe_load` only. [ ] Quality: secret scan clean (R13). [ ] Automated: secret-scan script.

### Phase 10 — Documentation & Deliverables
- **Refs:** §1, §11. **Inventory:** R53, R54 (doc), R49.
- Steps: 10.1 README: "Sampler & YAML playlists" section (flags, YAML schema, leading semantics, exit code 8, save output).
  10.2 Ship a `docs/examples/playlist.yaml` sample. 10.3 Confirm PRD/PLAN authoritative; document non-goals (R49).
- **Gate:** [ ] Func: README commands run as written; sample YAML validates. [ ] Quality: uv-only docs (R14). [ ] Automated: n/a.

### Phase 11 — Release & Verification — all 14 + ACs
- **Refs:** §1.3, §13. **Inventory:** R52, R54, S1–S4.
- Steps: 11.1 `uv sync`; ruff; `pytest --cov` (≥85%); file-size ≤150; secret-scan. 11.2 Manual (VLC):
  `--sample-play --dir .\downloads`; `--playlist-file sample.yaml` with `output.save: true` → one file in `target_folder`;
  `display: true` → VLC plays. 11.3 Confirm non-goals respected (R49). 11.4 Sign-Off + Quality Matrix; commit + push + tag.
- **Gate:** [ ] Func: S1–S4 met. [ ] Quality: 14/14 (§10); 100% coverage (§9). [ ] Automated: full gate suite.

---

## 6. Deliverables

| Deliverable | Producing Phase |
|-------------|-----------------|
| `pyyaml` dep + v1.03 versions + module skeletons | Phase 2 |
| `sample` + `render` config blocks + constants | Phase 3 |
| `MixSegment`, `PlaylistError`, segment-aware engines, `MixRenderer` | Phase 4 |
| `Sampler`, `services/playlist/{model,loader,summary}` | Phase 5 |
| SDK `sample_play`/`play_playlist` + wiring | Phase 6 |
| CLI `--sample-play`/`--play-for-sec`/`--playlist-file` + exit 8 | Phase 7 |
| Test suite ≥85% | Phase 8 |
| README section + `docs/examples/playlist.yaml` | Phase 10 |
| Verified, pushed, tagged release | Phase 11 |

---

## 7. Dependencies & External Integrations

| Dependency | Type | Phase |
|------------|------|-------|
| `pyyaml` | runtime (YAML parse) | 2–5 |
| FFmpeg (imageio-ffmpeg, reused) | render + probe | 4–5 |
| VLC / libVLC (external prereq) | display + stream | 6, 11 |
| `pytest`/`pytest-cov`/`ruff` | dev/test | 2–8 |
| YouTube (member URLs, via `ApiGatekeeper`) | network | 4 |

---

## 8. Open Questions

_None._ The PRD fully specifies behavior; the four design decisions (output-mode build order, local-loopback
streaming, leading-track master/mute/strip semantics, random-mid-band sampling) were resolved during PRD authoring.

---

## 9. PRD Coverage Matrix

| PRD Ref | Atomic Demand | Type | Primary Phase | Secondary | Verification |
|---------|---------------|------|---------------|-----------|--------------|
| §3.1 (R1) | `--sample-play` flag + mode | Func | 7 | 6 | 7.1 |
| §3.2 (R2) | sample scan reuse `PlaylistEngine.scan` + drive guard; bad dir→2 | Func | 5 | 7 | 5.1 |
| §3.2 (R3) | sample probe duration per clip | Func | 5 | 4 | 5.1 |
| §3.2 (R4) | random mid-band start, injectable RNG, config band | Func | 5 | 3 | 5.1 |
| §3.2 (R5) | play `sample.play_seconds`(10) or `--play-for-sec` | Func | 5 | 3 | 5.1 |
| §3.2 (R6) | crossfade video+audio between samples | Func | 4 | 5 | 4.3 |
| §3.2 (R7) | loop folder by default (`sample.loop`) | Func | 5 | 6 | 5.1 |
| §3.2 (R8) | Sampler emits MixSegments→engine (mode default option2) | Func | 5 | 6 | 5.1 |
| §4 (R9) | `--play-for-sec N` float seconds | Func | 7 | 5 | 7.1 |
| §4 (R10) | play-for-sec works with mix/sample + member default; overrides config | Func | 5 | 6,7 | 5.1 |
| §5.1 (R11) | `--playlist-file` flag | Func | 7 | 6 | 7.1 |
| §5.3 (R12) | YAML load+validate → `PlaylistError`/exit 8 | Func | 5 | 7 | 5.3 |
| §5.3 (R13) | order members by `id` | Func | 5 | — | 5.3 |
| §5.3 (R14) | resolve member `file` rel→`source_folder` | Func | 5 | — | 5.3 |
| §5.3 (R15) | build `MixSegment`s from members | Func | 5 | 4 | 5.3 |
| §5.3 (R16) | mix toggles gate streams (video/audio/subtitle) | Func | 5 | 6 | 5.4 |
| §5.3 (R17) | leading=video: picture+length master; **mute leading audio**; members supply audio | Func | 5 | 4 | 5.4 |
| §5.3 (R18) | leading=audio: audio+length master; video-file picture stripped, audio-only; members supply video | Func | 5 | 4 | 5.4 |
| §5.3 (R19) | leading=none: standard mix; length=Σplay−(N−1)·crossfade | Func | 5 | 4 | 5.4 |
| §5.3 (R20) | output display (VLC live) | Func | 6 | 4 | 6.1 |
| §5.3 (R21) | output save (one file→target_folder; once even if loop) | Func | 6 | 4 | 6.1 |
| §5.3 (R22) | output stream (local VLC loopback) | Func | 6 | 4 | 6.1 |
| §5.3 (R23) | output combos allowed | Func | 6 | — | 6.1 |
| §5.3 (R24) | loop honored (live) | Func | 6 | 5 | 6.1 |
| §5.2 (R25) | summary: length/size/resolution/members; report+write back | Func | 5 | 6 | 5.5 |
| §2 (R26) | `MixSegment` dataclass fields | Arch | 4 | — | 4.1 |
| §2 (R27) | engines/renderer consume segments (per-clip -ss/-t/offset/speed/scale/subs) | Arch | 4 | 5 | 4.3/4.4 |
| §2 (R28) | additive — v1.02 engines/tests stay green | Arch/R2 | 4 | 8 | 4.3 |
| §6 (R29) | MixRenderer continuous FFmpeg graph (xfade+acrossfade cumulative) | Func | 4 | — | 4.4 |
| §6 (R30) | leading-video render: keep picture, `-an` drop audio, audio=members mix | Func | 4 | 5 | 4.4 |
| §6 (R31) | leading-audio render: `-vn` audio-only, video=members xfade over audio length | Func | 4 | 5 | 4.4 |
| §6 (R32) | render container/codecs from `render` config → target_folder | Func | 4 | 3 | 4.4 |
| §6 (R33) | renderer reuse FfmpegLocator+probe_duration; subprocess injected | Arch | 4 | — | 4.4 |
| §12 (R34) | renderer normalizes scale/fps/setsar before xfade | Func | 4 | — | 4.4 |
| §7 (R35) | new `segment.py`/`sampler.py` | Arch | 2 | 4,5 | 2.3 |
| §7 (R36) | `services/playlist` pkg model/loader/summary | Arch | 2 | 5 | 2.3 |
| §7 (R37) | `infra/playback/renderer.py` | Arch | 2 | 4 | 2.3 |
| §7 (R38) | SDK `sample_play`/`play_playlist` + wiring | Arch/R1 | 6 | — | 6.1/6.2 |
| §7 (R39) | CLI flags + routing + usage | Arch | 7 | — | 7.1/7.3 |
| §7 (R40) | reuse scan/selection/ffmpeg/probe/locator/config/gatekeeper | Arch/R2 | 4 | 5 | 4.x |
| §7 (R41) | every file ≤150 LOC | Arch/R8 | 2–7 | — | standing gate |
| §8.1 (R42) | `setup.json` `sample` block | Config | 3 | — | 3.2 |
| §8.1 (R43) | `setup.json` `render` block | Config | 3 | — | 3.2 |
| §8.2 (R44) | version bumps 1.03 (+SUPPORTED) | Config/R6 | 2 | 3 | 2.2 |
| §8.2 (R45) | all tunables via `ConfigManager.get` | Config/R11 | 3 | Review | 3.x |
| §9 (R46) | exit code 8 + `PlaylistError` | Func | 4 | 7 | 4.2/7.2 |
| §10 (R47) | `uv add pyyaml` | Tool/R14 | 2 | — | 2.1 |
| §10 (R48) | no new secrets; reuse `.env` | Security/R13 | 9 | — | 9.2 |
| §1.4/§12 (R49) | non-goals respected (no GUI/RTMP/alpha/styling/HW) | Constraint | 11 | 10 | 11.3 |
| §13 (R50) | mirror tests; mock YAML/FFmpeg/VLC/probe/RNG/clock | Test/R7 | 8 | 4–7 | 8.1 |
| §13 (R51) | validations (malformed→8, sampler determinism, override, toggles, leading, argv, summary) | Test | 8 | 5 | 8.2 |
| §13 (R52) | gates ruff0/coverage≥85/≤150/uv | Quality | 8 | 11 | 8.3 |
| §11 (R53) | 14-rule compliance matrix | Deliverable | 10 | 11 | §10 |
| §13 (R54) | manual verification (sample plays; save→file; display→VLC) | AC | 11 | — | 11.2 |
| §5.2/§5.3 (R55) | validate playlist `version` field → exit 8 | Func | 5 | 7 | 5.3 |
| §5.3 (R56) | validate member file exists + removable-drive guard → exit 2 | Func | 5 | 7 | 5.3 |

**Coverage: 56/56 atomic demands mapped (100%).**

> **Changelog**
> - **1.01 (2026-06-20):** Audit back-propagation (`/new:todo-vs-prd`). Added R55 (validate playlist `version`
>   field → exit 8) and R56 (validate member file existence + `D:`/`H:` removable-drive guard → exit 2) to
>   Phase 5.3 + its gate + the coverage matrix.
> - **1.00 (2026-06-20):** Initial plan from `docs/PRD-playlist.md`.

---

## 10. Quality Verification Matrix (14 Rules)

| Rule # | Rule | Enforced In Phase(s) | Verification Method | Automated Check |
|--------|------|----------------------|---------------------|-----------------|
| 1 | SDK Architecture | 4, 6, 7 | `sample_play`/`play_playlist` on SDK; CLI delegates | grep: no business logic / engine imports in `cli/` |
| 2 | OOP / No Duplication | 4, 5, Review | `MixSegment` reuse; reuse scan/selection/ffmpeg/engines | code review; duplication scan |
| 3 | API Gatekeeper | 4 | member URLs via `ApiGatekeeper` | reuse path test |
| 4 | Rate-Limit Config | 3 | reuses `rate_limits.json` | config check |
| 5 | Queue Management | 4 | reuses `DownloadQueue` | reuse test |
| 6 | Version Control | 2 | code+config → 1.03; validation | grep version; config test |
| 7 | TDD | 3–8 | tests-first; happy+error | `uv run pytest tests/` |
| 8 | File Size ≤150 | 2–7 | module split by design | file-size script |
| 9 | Coverage ≥85% | 8 | `fail_under=85` | `uv run pytest --cov=src` |
| 10 | Ruff | 2–7 | ruff config | `uv run ruff check src/ tests/` |
| 11 | No Hardcoded | 3, Review | sample/render via config | grep literals; config-driven test |
| 12 | Config Architecture | 3 | `sample`+`render` blocks; constants | structure check |
| 13 | Secrets | 9 | `safe_load`; no secrets | secret-scan |
| 14 | uv | 2 | `uv add pyyaml`; uv.lock | uv-toolchain scan |

**All 14 rules enforced (14/14).**

---

## 11. Sign-Off

| Check | Status | Evidence |
|-------|--------|----------|
| 100% PRD coverage | PASS | §9 (56/56) |
| 14/14 rules enforced | PASS | §10 |
| No open questions | PASS | §8 (none) |
| All phase gates defined | PASS | §5 (Phases 1–11) |
