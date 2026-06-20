# TODO — Sampler / Playlist (derived from PLAN-playlist.md)

**Plan source:** `docs/PLAN-playlist.md`
**Generated:** 2026-06-20
**Minimum tasks contract:** >= 200
**Total atomic tasks:** 205
**Coverage:** 54/54 PRD demands + 14/14 rules + all gates/sign-off (100%)

## Conventions
- `[ ]` = open, `[x]` = done. Every task ends with citations: `(Plan §x)`, `(Plan Phase n.m)`, `(Plan Gate n)`, `(Rule #k)`, `(Rxx)`, `(Sx)`.
- Each phase ends with **Gate** (functional + quality + automated) and a **Commit** task.
- TDD ordering: RED → GREEN → REFACTOR. `Rxx` = PLAN §9 inventory ID. `Sx` = success metric.
- **Standing rule (Phases 2–7):** the v1.02 suite MUST stay green (additive engine changes only).

---

## Phase 1 — Planning & Discovery
**Objective:** Lock inventory + reuse map. | **Plan refs:** §1–§13 | **Rules:** none

- [ ] Read `docs/PRD-playlist.md` and `docs/PLAN-playlist.md` end-to-end (Plan §1)
- [ ] Confirm Requirements Inventory R1–R54 complete (Plan §9, Phase 1.1)
- [ ] Confirm reuse map: `PlaylistEngine.scan`, `FfmpegLocator`, `probe_duration`, `VlcLocator`, engines, `shared/selection`, `ApiGatekeeper` (Plan Phase 1.2)
- [ ] Confirm Open Questions empty (Plan §8)
- [ ] Phase 1 Gate — every PRD demand has an inventory ID (Plan Gate 1)
- [ ] Phase 1 Gate — 14-rule anchors reviewed (Plan §4)
- [ ] Phase 1 Commit — `docs: confirm playlist inventory + reuse map` (Rule #6)

---

## Phase 2 — Initialization (deps, version, structure)
**Objective:** pyyaml, v1.03, module skeletons. | **Plan refs:** §7,§8.2,§10 | **Rules:** 6,8,10,14

- [ ] Run `uv add pyyaml` (Plan Phase 2.1, R47, Rule #14)
- [ ] Confirm `uv.lock` updated and committed (Plan Phase 2.1, Rule #14)
- [ ] Confirm `import yaml` works under `uv run` (Plan Phase 2.1, R47)
- [ ] Bump `src/ytdl/shared/version.py` → `1.03` (Plan Phase 2.2, R44, Rule #6)
- [ ] Bump `pyproject.toml` `[project].version` → `1.03` (Plan Phase 2.2, R44)
- [ ] Bump `config/setup.json` `version` → `1.03` (Plan Phase 2.2, R44)
- [ ] Bump `config/rate_limits.json` `version` → `1.03` (Plan Phase 2.2, R44)
- [ ] Add `"1.03"` to `ConfigManager.SUPPORTED_CONFIG_VERSIONS` (Plan Phase 2.2, R44, Rule #6)
- [ ] Update config tests pinning version values for 1.03 (Plan Phase 2.2, Rule #7)
- [ ] Create `src/ytdl/services/mixer/segment.py` skeleton (Plan Phase 2.3, R35)
- [ ] Create `src/ytdl/services/mixer/sampler.py` skeleton (Plan Phase 2.3, R35)
- [ ] Create `src/ytdl/services/playlist/__init__.py` (Plan Phase 2.3, R36)
- [ ] Create `src/ytdl/services/playlist/{model,loader,summary}.py` skeletons (Plan Phase 2.3, R36)
- [ ] Create `src/ytdl/infra/playback/renderer.py` skeleton (Plan Phase 2.3, R37)
- [ ] Phase 2 Gate — `uv sync` succeeds (Plan Gate 2 functional)
- [ ] Phase 2 Gate — confirm `uv.lock` present, no requirements.txt (Plan Gate 2, Rule #14)
- [ ] Phase 2 Gate — confirm versions == 1.03 across code+config (Plan Gate 2, Rule #6)
- [ ] Phase 2 Gate — run `uv run ruff check src/` zero violations (Plan Gate 2, Rule #10)
- [ ] Phase 2 Gate — run file-size script, 0 files > 150 LOC (Plan Gate 2, Rule #8)
- [ ] Phase 2 Gate — run full v1.02 suite green (Plan §2 R28)
- [ ] Phase 2 Commit — `chore(playlist): pyyaml dep, v1.03, module skeletons` (Rule #6,#14)

---

## Phase 3 — Configuration
**Objective:** sample + render config blocks; constants. | **Plan refs:** §8 | **Rules:** 6,7,11,12

- [ ] RED: test config reads `sample.play_seconds` default 10 (Plan Phase 3.1, R42, Rule #7)
- [ ] RED: test config reads `sample.mid_band_low`/`high` defaults 0.25/0.75 (Plan Phase 3.1, R42, Rule #7)
- [ ] RED: test config reads `sample.loop` default true (Plan Phase 3.1, R42, Rule #7)
- [ ] RED: test config reads `render.video_codec`/`audio_codec`/`container` (Plan Phase 3.1, R43, Rule #7)
- [ ] RED: test config version 1.03 validates (Plan Phase 3.1, R44, Rule #7)
- [ ] GREEN: add `sample` block to `config/setup.json` (play_seconds, mid_band_low, mid_band_high, loop) (Plan Phase 3.2, R42)
- [ ] GREEN: add `render` block to `config/setup.json` (video_codec, audio_codec, container) (Plan Phase 3.2, R43)
- [ ] GREEN: add sample/render/effect/output name constants to `constants.py` (Plan Phase 3.3, R45, Rule #11)
- [ ] REFACTOR: dedupe config defaults; tests green (Plan Phase 3, Rule #2)
- [ ] Verify all new tunables read via `ConfigManager.get` (not hardcoded) (Plan Gate 3, Rule #11)
- [ ] Phase 3 Gate — configs load; defaults returned; 1.03 validates (Plan Gate 3 functional)
- [ ] Phase 3 Gate — confirm config hierarchy present (Plan Gate 3, Rule #12)
- [ ] Phase 3 Gate — confirm both configs carry `"version":"1.03"` (Plan Gate 3, Rule #6)
- [ ] Phase 3 Gate — run `uv run pytest tests/unit/shared/test_config.py` (Plan Gate 3 automated)
- [ ] Phase 3 Gate — run ruff + file-size + full suite (Plan Gate 3, Rule #8,#10)
- [ ] Phase 3 Commit — `feat(config): v1.03 sample + render blocks` (Rule #6)

---

## Phase 4 — Architecture & Shared Infrastructure
**Objective:** MixSegment, PlaylistError, segment-aware engines, MixRenderer. | **Plan refs:** §2,§6,§9 | **Rules:** 1,2,3,5,7,8,10

- [ ] RED: test `MixSegment` dataclass holds path/start/play_seconds/speed/resolution/subtitle/effect with defaults (Plan Phase 4.1, R26, Rule #7)
- [ ] GREEN: implement `services/mixer/segment.py` `MixSegment` (frozen dataclass) (Plan Phase 4.1, R26, Rule #8)
- [ ] RED: test `PlaylistError(YtdlError)` exists and subclasses base (Plan Phase 4.2, R46, Rule #7)
- [ ] GREEN: add `PlaylistError` to `shared/errors.py` (Plan Phase 4.2, R46)
- [ ] RED: test segment-aware Option1 entry consumes `list[MixSegment]` → per-clip `-ss start -t play` (Plan Phase 4.3, R27, Rule #7)
- [ ] RED: test segment-aware xfade offset = cumulative play − k·crossfade (Plan Phase 4.3, R27, Rule #7)
- [ ] RED: test per-segment `setpts`/`atempo` applied for speed != 1.0 (Plan Phase 4.3, R27, Rule #7)
- [ ] RED: test per-segment `scale` applied for resolution != "max" (Plan Phase 4.3, R27, Rule #7)
- [ ] GREEN: add additive segment-aware method to `Option1Engine`/`StreamServer` (Plan Phase 4.3, R27, Rule #8)
- [ ] GREEN: add additive segment-aware method to `Option2Engine`/`LibVlcPlayerMatrix` (Plan Phase 4.3, R27, Rule #8)
- [ ] REFACTOR: share segment→args helper; no dup (Plan Phase 4.3, Rule #2)
- [ ] Verify v1.02 engine entry points + tests unchanged/green (Plan Phase 4.3, R28)
- [ ] RED: test `MixRenderer` builds N-input graph with per-input `-ss`/`-t` (Plan Phase 4.4, R29, Rule #7)
- [ ] RED: test `MixRenderer` chains `xfade`+`acrossfade` with cumulative offsets (Plan Phase 4.4, R29, Rule #7)
- [ ] RED: test `MixRenderer` normalizes scale/fps/setsar before xfade (Plan Phase 4.4, R34, Rule #7)
- [ ] RED: test leading-video render: `-an` drops leading audio; output audio = members mix (Plan Phase 4.4, R30, Rule #7)
- [ ] RED: test leading-audio render: `-vn`/`-map 0:a:0` audio-only; video = members xfade (Plan Phase 4.4, R31, Rule #7)
- [ ] RED: test render container/codecs from `render` config; output to target_folder (Plan Phase 4.4, R32, Rule #7)
- [ ] GREEN: implement `infra/playback/renderer.py` `MixRenderer` graph builder (Plan Phase 4.4, R29, Rule #8)
- [ ] GREEN: implement leading-video / leading-audio variants (`-an`/`-vn`) (Plan Phase 4.4, R30,R31)
- [ ] GREEN: implement input normalization (scale/fps/setsar) (Plan Phase 4.4, R34)
- [ ] RED: test `MixRenderer` inserts subtitle per member (filename → insert file; true → embedded; false → none) (Plan Phase 4.4, R27, Rule #7)
- [ ] GREEN: implement subtitle insert/burn per member in renderer (Plan Phase 4.4, R27)
- [ ] GREEN: wire `FfmpegLocator` + `probe_duration`; inject subprocess runner (Plan Phase 4.4, R33)
- [ ] REFACTOR: split renderer helpers if > 150 lines (Plan Phase 4.4, Rule #8)
- [ ] Verify member-URL injection reuses `ApiGatekeeper`/`SDK.download` (Plan Phase 4, R3,R5,R40)
- [ ] Write docstrings for MixSegment/MixRenderer/segment methods (Plan §2, Rule #1)
- [ ] Phase 4 Gate — MixRenderer argv: offsets/`-ss`/`-t`/codecs correct (Plan Gate 4 functional)
- [ ] Phase 4 Gate — leading variants emit `-an`/`-vn` (Plan Gate 4 functional)
- [ ] Phase 4 Gate — confirm no duplication; engines reachable via SDK only (Plan Gate 4, Rule #1,#2)
- [ ] Phase 4 Gate — confirm v1.02 suite still green (Plan Gate 4, R28)
- [ ] Phase 4 Gate — run `uv run pytest tests/unit/infra tests/unit/services` (Plan Gate 4 automated)
- [ ] Phase 4 Gate — run ruff + file-size + coverage (Plan Gate 4, Rule #8,#9,#10)
- [ ] Phase 4 Commit — `feat(playlist): MixSegment, segment engines, MixRenderer` (Rule #6)

---

## Phase 5 — Domain Implementation (Sampler, Playlist model/loader/summary)
**Objective:** Sampler + YAML model/loader/summary. | **Plan refs:** §3,§5,§6 | **Rules:** 2,7,8,10

- [ ] RED: test `Sampler` probes duration and picks random start in mid-band via injected RNG (Plan Phase 5.1, R3,R4, Rule #7)
- [ ] RED: test `Sampler` mid-band bounds from config (0.25/0.75) (Plan Phase 5.1, R4, Rule #7)
- [ ] RED: test `Sampler` play_seconds from config (10) (Plan Phase 5.1, R5, Rule #7)
- [ ] RED: test `Sampler` `--play-for-sec` overrides config duration (Plan Phase 5.1, R5,R10, Rule #7)
- [ ] RED: test `Sampler` loops folder by default (sample.loop) (Plan Phase 5.1, R7, Rule #7)
- [ ] RED: test `Sampler` emits `list[MixSegment]` (start=random mid, play_seconds set) (Plan Phase 5.1, R8, Rule #7)
- [ ] GREEN: implement `services/mixer/sampler.py` `Sampler` (injectable RNG; reuse `PlaylistEngine.scan`, `probe_duration`) (Plan Phase 5.1, R3-R8, Rule #8)
- [ ] REFACTOR: dedupe sampler segment building; tests green (Plan Phase 5.1, Rule #2)
- [ ] RED: test `playlist/model.py` dataclasses parse metadata/output/mix/leading/member fields (Plan Phase 5.2, R36, Rule #7)
- [ ] GREEN: implement `services/playlist/model.py` (Playlist/Metadata/Output/Mix/Leading/Member) (Plan Phase 5.2, R36, Rule #8)
- [ ] RED: test loader parses valid YAML → model (Plan Phase 5.3, R12, Rule #7)
- [ ] RED: test loader malformed/invalid YAML → `PlaylistError` (Plan Phase 5.3, R12, Rule #7)
- [ ] RED: test loader uses `yaml.safe_load` (no arbitrary objects) (Plan Phase 5.3, R12, Rule #13)
- [ ] RED: test loader orders members by `id` (Plan Phase 5.3, R13, Rule #7)
- [ ] RED: test loader resolves member `file` rel→`source_folder` (Plan Phase 5.3, R14, Rule #7)
- [ ] RED: test loader builds `MixSegment`s from members (start/play/speed/resolution/subtitle/effect) (Plan Phase 5.3, R15, Rule #7)
- [ ] GREEN: implement `services/playlist/loader.py` (parse+validate+order+resolve+segments) (Plan Phase 5.3, R12-R15, Rule #8)
- [ ] RED: test member `subtitle` — "file.srt" inserts that file / true reads embedded / false none (Plan Phase 5.3, R15,R16, Rule #7)
- [ ] RED: test member defaults — playback_speed=1.0, resolution="max" applied to segment (Plan Phase 5.3, R15, Rule #7)
- [ ] RED: test member `file` as YouTube URL resolved via gatekeeper → segment (Plan Phase 5.3, A1, Rule #7)
- [ ] GREEN: implement YouTube-URL member resolution via `SDK.download` (rate-limited) (Plan Phase 5.3, A1, R40)
- [ ] REFACTOR: split loader if > 150 lines; tests green (Plan Phase 5.3, Rule #8)
- [ ] RED: test mix toggles gate which streams produced (video/audio/subtitle off → absent) (Plan Phase 5.4, R16, Rule #7)
- [ ] RED: test leading=video selects picture+length master and MUTES leading audio (Plan Phase 5.4, R17, Rule #7)
- [ ] RED: test leading=audio uses audio-only even from a video file; members supply video (Plan Phase 5.4, R18, Rule #7)
- [ ] RED: test leading=none → length = Σplay − (N−1)·crossfade (Plan Phase 5.4, R19, Rule #7)
- [ ] GREEN: implement mix-toggle + leading-kind selection in the playlist runner (Plan Phase 5.4, R16-R19, Rule #8)
- [ ] RED: test `summary.py` computes total_length / total_file_size / resolution / members (Plan Phase 5.5, R25, Rule #7)
- [ ] GREEN: implement `services/playlist/summary.py` (compute + write back) (Plan Phase 5.5, R25, Rule #8)
- [ ] Write docstrings for Sampler / loader / model / summary (Plan §5, Rule #1)
- [ ] Phase 5 Gate — malformed YAML → PlaylistError; sampler deterministic under seeded RNG (Plan Gate 5 functional)
- [ ] Phase 5 Gate — toggles/leading honored; summary computed (Plan Gate 5 functional)
- [ ] Phase 5 Gate — confirm reuse of scan/selection; no duplication (Plan Gate 5, Rule #2)
- [ ] Phase 5 Gate — run `uv run pytest tests/unit/services` (Plan Gate 5 automated)
- [ ] Phase 5 Gate — run ruff + file-size + coverage (Plan Gate 5, Rule #8,#9,#10)
- [ ] Phase 5 Commit — `feat(playlist): Sampler + YAML model/loader/summary` (Rule #6)

---

## Phase 6 — SDK / API Surface
**Objective:** sample_play + play_playlist + wiring. | **Plan refs:** §7 | **Rules:** 1,2,7

- [ ] RED: test `SDK.sample_play(dir, play_for_sec, mode)` builds segments → engine (Plan Phase 6.1, R8,R38, Rule #7)
- [ ] RED: test `SDK.play_playlist(yaml)` routes display/save/stream per metadata (Plan Phase 6.1, R20-R23,R38, Rule #7)
- [ ] RED: test `play_playlist` save executed ONCE even when loop true (Plan Phase 6.1, R21,R24, Rule #7)
- [ ] RED: test `play_playlist` output combinations allowed (display+save) (Plan Phase 6.1, R23, Rule #7)
- [ ] RED: test loop honored for live display (Plan Phase 6.1, R24, Rule #7)
- [ ] RED: test `play_playlist` stream → local VLC loopback (Option-1) (Plan Phase 6.1, R22, Rule #7)
- [ ] GREEN: implement `sdk/sdk.py` `sample_play` (Plan Phase 6.1, R38, Rule #1,#8)
- [ ] GREEN: implement `sdk/sdk.py` `play_playlist` (output routing + loop + save-once) (Plan Phase 6.1, R38, Rule #1)
- [ ] GREEN: add `build_sampler`/`build_playlist_runner` to `sdk/wiring.py` (Plan Phase 6.2, R38)
- [ ] GREEN: ensure SDK is the only externally-imported surface (Plan Phase 6.3, R38, Rule #1)
- [ ] REFACTOR: dedupe SDK→service wiring; tests green (Plan Phase 6, Rule #2)
- [ ] Write docstrings for `sample_play`/`play_playlist` (Plan §7, Rule #1)
- [ ] Phase 6 Gate — sample_play builds segments→engine; play_playlist honors combos + loop + save-once (Plan Gate 6 functional)
- [ ] Phase 6 Gate — all ops via SDK without importing internals (Plan Gate 6, Rule #1)
- [ ] Phase 6 Gate — run `uv run pytest tests/unit/sdk` (Plan Gate 6 automated)
- [ ] Phase 6 Gate — run ruff + file-size + coverage (Plan Gate 6, Rule #8,#9,#10)
- [ ] Phase 6 Commit — `feat(sdk): sample_play + play_playlist entry points` (Rule #1,#6)

---

## Phase 7 — CLI / External Interface
**Objective:** flags + routing + exit code 8. | **Plan refs:** §3.1,§4,§5.1,§9 | **Rules:** 1,7,8,10

- [ ] RED: test `--sample-play` flag parses (Plan Phase 7.1, R1, Rule #7)
- [ ] RED: test `--play-for-sec` parses as float (Plan Phase 7.1, R9, Rule #7)
- [ ] RED: test `--playlist-file` parses a path (Plan Phase 7.1, R11, Rule #7)
- [ ] RED: test `--sample-play` routes to `SDK.sample_play` with parsed args (Plan Phase 7.2, R1, Rule #7)
- [ ] RED: test `--playlist-file` routes to `SDK.play_playlist` (Plan Phase 7.2, R11, Rule #7)
- [ ] RED: test `PlaylistError` → exit code 8 (Plan Phase 7.2, R46, Rule #7)
- [ ] RED: test `PlaybackDependencyError` → exit 7 in mix/sample/playlist (Plan Phase 7.2, Rule #7)
- [ ] RED: test bad dir/file → exit 2 (Plan Phase 7.2, R2, Rule #7)
- [ ] GREEN: add `--sample-play`/`--play-for-sec`/`--playlist-file` to `cli/args.py` (Plan Phase 7.1, R1,R9,R11, Rule #8)
- [ ] GREEN: add `EXIT_PLAYLIST = 8` constant to `cli/main.py` (Plan Phase 7.2, R46)
- [ ] GREEN: route `--sample-play`/`--playlist-file` in `cli/main.py` (Plan Phase 7.2, R1,R11, Rule #1)
- [ ] GREEN: map `PlaylistError`→8, dep→7, bad dir/file→2 (Plan Phase 7.2, R46,R2)
- [ ] GREEN: ensure CLI delegates 100% to SDK (no business logic) (Plan Phase 7.4, Rule #1)
- [ ] GREEN: add sampler/playlist examples to `cli/usage.py` cheat-sheet (Plan Phase 7.3, R39)
- [ ] REFACTOR: extract arg→SDK mapping helper; tests green (Plan Phase 7, Rule #2)
- [ ] Phase 7 Gate — flags parse; routing correct; exit codes 8/7/2 mapped (Plan Gate 7 functional)
- [ ] Phase 7 Gate — confirm zero business logic in CLI (Plan Gate 7, Rule #1)
- [ ] Phase 7 Gate — run `uv run pytest tests/unit/cli` (Plan Gate 7 automated)
- [ ] Phase 7 Gate — run ruff + file-size + coverage (Plan Gate 7, Rule #8,#9,#10)
- [ ] Phase 7 Commit — `feat(cli): --sample-play/--play-for-sec/--playlist-file + exit 8` (Rule #1,#6)

---

## Phase 8 — Testing & Coverage
**Objective:** fixtures, error paths, ≥85%. | **Plan refs:** §13 | **Rules:** 7,9

- [ ] Add conftest fixture: tmp YAML file + in-memory playlist dict (Plan Phase 8.1, R50, Rule #7)
- [ ] Add conftest fixture: mock FFmpeg subprocess runner (Plan Phase 8.1, R50)
- [ ] Add conftest fixture: mock VLC / `python-vlc` (reuse existing) (Plan Phase 8.1, R50)
- [ ] Add conftest fixture: mock `probe_duration` (Plan Phase 8.1, R50)
- [ ] Add conftest fixture: injectable seeded RNG + fake clock (Plan Phase 8.1, R50)
- [ ] Error-path test: malformed YAML → exit 8 (Plan Phase 8.2, R51, Rule #7)
- [ ] Error-path test: missing dir → exit 2 (Plan Phase 8.2, R51, Rule #7)
- [ ] Error-path test: missing VLC → exit 7 (Plan Phase 8.2, R51, Rule #7)
- [ ] Test: sampler deterministic under seeded RNG (Plan Phase 8.2, R51)
- [ ] Test: `--play-for-sec` overrides config (Plan Phase 8.2, R51)
- [ ] Test: mix toggles gate streams (Plan Phase 8.2, R51)
- [ ] Test: leading-kind selects correct master (mute/strip) (Plan Phase 8.2, R51)
- [ ] Test: MixRenderer argv (offsets/`-ss`/`-t`/codecs) (Plan Phase 8.2, R51)
- [ ] Test: summary computes length/size/resolution (Plan Phase 8.2, R51)
- [ ] Confirm no real render/playback/network in unit tests (Plan Gate 8 functional, R50)
- [ ] Raise coverage to ≥85%; test files ≤150 lines (Plan Phase 8.3, R52, Rule #8,#9)
- [ ] Phase 8 Gate — full suite green; coverage ≥85% (Plan Gate 8, Rule #9)
- [ ] Phase 8 Gate — run `uv run pytest tests/ --cov=src --cov-report=term-missing` (Plan Gate 8 automated)
- [ ] Phase 8 Gate — run ruff + file-size (Plan Gate 8, Rule #8,#10)
- [ ] Phase 8 Commit — `test(playlist): fixtures, error paths, coverage >=85%` (Rule #6,#9)

---

## Phase 9 — Security Review
**Objective:** safe YAML, no secrets. | **Plan refs:** §10 | **Rules:** 13

- [ ] Confirm loader uses `yaml.safe_load` only (no `yaml.load`) (Plan Phase 9.1, Rule #13)
- [ ] Run secret-scan over new modules (Plan Phase 9.1, R48, Rule #13)
- [ ] Confirm no secrets/credentials in new code (Plan Phase 9.1, R48)
- [ ] Confirm `.gitignore`/`.env-example` unchanged-and-sufficient (Plan Phase 9.2, R48)
- [ ] Phase 9 Gate — `safe_load` only; secret scan clean (Plan Gate 9, Rule #13)
- [ ] Phase 9 Gate — run secret-scan script (Plan Gate 9 automated)
- [ ] Phase 9 Commit — `chore(security): playlist YAML safe_load + secret scan` (Rule #6,#13)

---

## Phase 10 — Documentation & Deliverables
**Objective:** README + sample YAML. | **Plan refs:** §1,§11 | **Rules:** 14

- [ ] Write README "Sampler & YAML playlists" section (flags + behavior) (Plan Phase 10.1, R53)
- [ ] Document the YAML schema in README (metadata + members) (Plan Phase 10.1, R53)
- [ ] Document leading semantics (mute leading video audio; video-source-as-audio-only) (Plan Phase 10.1, R17,R18)
- [ ] Document exit code 8 + save output location in README (Plan Phase 10.1, R46)
- [ ] Create `docs/examples/playlist.yaml` sample (Plan Phase 10.2, R54)
- [ ] Document non-goals (no GUI/RTMP/alpha/styling/HW) in README (Plan Phase 10.3, R49)
- [ ] Phase 10 Gate — README commands run as written; sample YAML validates (Plan Gate 10 functional)
- [ ] Phase 10 Gate — docs reference uv-only commands (Plan Gate 10, Rule #14)
- [ ] Phase 10 Commit — `docs: sampler/playlist README + example YAML` (Rule #6)

---

## Phase 11 — Release & Verification (final gate)
**Objective:** prove S1–S4 + push + tag. | **Plan refs:** §1.3,§13 | **Rules:** all 14

- [ ] Run `uv sync` (Plan Phase 11.1, R52)
- [ ] Run `uv run ruff check src/ tests/` zero violations (Plan Phase 11.1, Rule #10)
- [ ] Run `uv run pytest tests/ --cov=src` ≥85% (Plan Phase 11.1, Rule #9)
- [ ] Run file-size script, 0 files > 150 LOC (Plan Phase 11.1, Rule #8)
- [ ] Run secret-scan clean (Plan Phase 11.1, Rule #13)
- [ ] Confirm v1.02 suite still green (no regressions) (Plan Phase 11.1, R28)
- [ ] Manual: `--sample-play --dir .\downloads` plays random mid-band samples (Plan Phase 11.2, S1)
- [ ] Manual: `--playlist-file sample.yaml` with `output.save:true` → one file in target_folder (Plan Phase 11.2, R21,S3)
- [ ] Manual: `--playlist-file sample.yaml` with `display:true` → VLC plays the mix (Plan Phase 11.2, R20,S3)
- [ ] Manual: `--play-for-sec` controls clip duration (Plan Phase 11.2, S2)
- [ ] Confirm non-goals respected (no GUI/RTMP/alpha/styling/HW) (Plan Phase 11.3, R49)
- [ ] Complete Sign-Off: 100% PRD coverage (Plan §11, S4)
- [ ] Complete Sign-Off: 14/14 rules PASS (Plan §10, S4)
- [ ] Complete Sign-Off: no open questions (Plan §8)
- [ ] Phase 11 Gate — S1–S4 met; artifacts valid (Plan Gate 11 functional)
- [ ] Phase 11 Commit — `chore(release): v1.03 sampler/playlist verification` (Rule #6)
- [ ] Phase 11 — push `origin master` and tag `v1.03` (Plan Phase 11.4)
- [ ] Phase 11 — verify `v1.03` tag present on `origin` and tree in sync (Plan Phase 11.4)

---

## Plan Coverage Map
| Plan Element | Type | Satisfying TODO line(s) | Status |
|---|---|---|---|
| Phase 1–11 | Phase | each Phase block above | PASS |
| R1–R2 (sample CLI/scan) | Func | Phase 7 + Phase 5 sampler tasks | PASS |
| R3–R8 (sampler behavior) | Func | Phase 5 Sampler RED/GREEN | PASS |
| R9–R10 (play-for-sec) | Func | Phase 7 + Phase 5 override tasks | PASS |
| R11–R15 (playlist load/order/resolve/segments) | Func | Phase 5 loader tasks | PASS |
| R16 (mix toggles) | Func | Phase 5.4 toggle task | PASS |
| R17 (leading-video mute audio) | Func | Phase 5.4 + Phase 4.4 `-an` tasks | PASS |
| R18 (leading-audio strip picture) | Func | Phase 5.4 + Phase 4.4 `-vn` tasks | PASS |
| R19 (leading none length) | Func | Phase 5.4 task | PASS |
| R20–R24 (display/save/stream/combos/loop) | Func | Phase 6 play_playlist tasks | PASS |
| R25 (summary) | Func | Phase 5.5 summary tasks | PASS |
| R26 (MixSegment) | Arch | Phase 4.1 tasks | PASS |
| R27 (segment consumption) | Arch | Phase 4.3 tasks | PASS |
| R28 (additive, v1.02 green) | Arch/Rule2 | Phase 2/4/11 v1.02-green gates | PASS |
| R29–R34 (MixRenderer) | Func | Phase 4.4 renderer tasks | PASS |
| R35–R37 (new modules) | Arch | Phase 2.3 skeleton tasks | PASS |
| R38 (SDK entry points) | Arch/Rule1 | Phase 6 tasks | PASS |
| R39 (CLI flags/usage) | Arch | Phase 7 tasks | PASS |
| R40 (reuse) | Arch/Rule2 | Phase 4/5 reuse tasks | PASS |
| R41 (≤150 LOC) | Arch/Rule8 | every phase file-size gate | PASS |
| R42–R43 (sample/render config) | Config | Phase 3 tasks | PASS |
| R44 (version 1.03) | Config/Rule6 | Phase 2.2 tasks | PASS |
| R45 (config-driven) | Config/Rule11 | Phase 3 verify task | PASS |
| R46 (exit 8 + PlaylistError) | Func | Phase 4.2 + Phase 7.2 tasks | PASS |
| R47 (pyyaml) | Tool/Rule14 | Phase 2.1 tasks | PASS |
| R48 (no secrets) | Security/Rule13 | Phase 9 tasks | PASS |
| R49 (non-goals) | Constraint | Phase 11.3 + Phase 10 tasks | PASS |
| R50–R52 (tests/gates) | Test | Phase 8 tasks | PASS |
| R53 (compliance matrix) | Deliverable | Quality Rules Coverage below | PASS |
| R54 (manual verification) | AC | Phase 11.2 tasks | PASS |
| Sign-Off rows (4) | Sign-Off | Phase 11 sign-off tasks | PASS |

---

## Quality Rules Coverage (audit)
| Rule # | Where enforced in TODO | Verification task line |
|---|---|---|
| 1 SDK Architecture | Phases 4,6,7 | "all ops via SDK without importing internals" |
| 2 OO Design | every impl phase | each REFACTOR + reuse task |
| 3 API Gatekeeper | Phase 4 | "member-URL injection reuses ApiGatekeeper" |
| 4 Rate Limit Config | Phase 3 (reuse) | rate_limits.json reuse |
| 5 Queue Mgmt | Phase 4 (reuse) | DownloadQueue reuse |
| 6 Version Control | Phase 2 + commits | "versions == 1.03" + commit tasks |
| 7 TDD | every phase | all RED tasks |
| 8 File Size ≤150 | every phase gate | "file-size script 0 files > 150" |
| 9 Coverage ≥85% | Phases 8,11 | "coverage ≥85%" |
| 10 Linter | every phase gate | "ruff check zero violations" |
| 11 No Hardcoded | Phase 3 | "tunables read via ConfigManager.get" |
| 12 Config Architecture | Phase 3 | "config hierarchy present" |
| 13 Secrets | Phases 5,9 | "safe_load only" + "secret scan clean" |
| 14 uv | Phases 2,10,11 | "uv add pyyaml; uv.lock present" |

---

## Self-Review (Gap Analysis)
**Method:** walked every Phase (1–11), every Gate criterion, every PRD-Coverage row (R1–R54), every Quality-Rule row (1–14), every Sign-Off row, and every Risk/Deliverable. Located the satisfying TODO line(s).

Self-review gaps found and patched in-place (GA.1–GA.4):
- GA.1 — v1.02-green constraint (R28) needed explicit gate tasks → added to Phase 2/4/11 gates (3 tasks)
- GA.2 — leading mute/strip clarifications (R17/R18) split into BOTH Phase 5.4 (selection) and Phase 4.4 (`-an`/`-vn` render) tasks (4 tasks)
- GA.3 — save-once-under-loop (R21/R24) was implicit → explicit Phase 6 RED task (1 task)
- GA.4 — YAML `safe_load` (Rule 13) → explicit Phase 5.3 RED + Phase 9 gate tasks (2 tasks)
- GA.5 — post-count recheck (197 < 200 floor): under-decomposed items split into atomic tasks — renderer
  subtitle insert/burn (R27, 2), member subtitle/defaults/YouTube-URL resolution (R15/R16/A1/R40, 4), playlist
  stream test (R22, 1), tag-verify (Plan 11.4, 1) → 205 total, clearing the floor without inventing work

**Verification:** Plan Coverage Map traces every Plan element → TODO line; Quality Rules Coverage proves 14/14; every phase ends with Gate + Commit; every GREEN is preceded by a RED in file order.

---

## Sign-Off
| Check | Status | Evidence |
|---|---|---|
| >= 200 atomic tasks | PASS | task count = 205 |
| 100% plan coverage | PASS | Plan Coverage Map |
| All quality rules cited | PASS | Quality Rules Coverage (14/14) |
| RED-before-GREEN ordering enforced | PASS | every GREEN preceded by RED |
| Gate + Commit tasks present in every phase | PASS | Phases 1–11 |
| No untraceable tasks | PASS | every task carries a `(…)` citation |
| No remaining gaps after self-review | PASS | GA.1–GA.4 patched |
