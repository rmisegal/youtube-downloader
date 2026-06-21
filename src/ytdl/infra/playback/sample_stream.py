"""Option-1 sample prep + xfade-stream orchestration (kept out of engines.py).

Prepares each clip's sample to a small normalized 720p ``.ts`` ONE AT A TIME
(the only heavy step) via :class:`SamplePrep`, SKIPPING any clip whose prep
fails; then xfade-stitches the small uniform clips into ONE ``vlc -`` window.
FFmpeg/VLC stderr is redirected to the size-capped subprocess log (or DEVNULL).
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ytdl.constants import ADVANCED_TEXT_EFFECTS
from ytdl.infra.playback.moviepy_tracks import render_moviepy_overlay
from ytdl.infra.playback.overlay_tracks import build_overlay_command
from ytdl.infra.playback.render_route import render_command
from ytdl.infra.playback.renderer import MixRenderer
from ytdl.infra.playback.stream_server import DEFAULT_VLC_BINARY
from ytdl.services.mixer.sample_prep import SamplePrep
from ytdl.services.mixer.segment import MixSegment


def _prepare_all(
    segments: list[MixSegment], sample_prep: SamplePrep, tmp_dir: str
) -> list[MixSegment]:
    """Prep each segment sequentially; return the prepared (succeeded) clips.

    Prints a keep-alive line per clip so a long prep never looks frozen.
    """
    prepared: list[MixSegment] = []
    total = len(segments)
    for index, seg in enumerate(segments):
        name = Path(seg.path).name
        print(f"[sample] preparing {index + 1}/{total}: {name}", flush=True)
        out_path = str(Path(tmp_dir) / f"{index:02d}.ts")
        if sample_prep.prepare(seg, out_path):
            # Carry ``at`` so the timeline compositor can place the prepped clip.
            prepared.append(
                MixSegment(path=out_path, start=0.0, play_seconds=seg.play_seconds, at=seg.at)
            )
        else:
            print(f"[sample] skipped (prep failed): {name}", flush=True)
    print(f"[sample] {len(prepared)}/{total} clips ready — launching VLC…", flush=True)
    return prepared


def _has_advanced_text(overlay: dict) -> bool:
    """True when any text element needs the MoviePy engine (zoom/rotate/per-letter…)."""
    return any((getattr(el, "effect", "") or "").lower() in ADVANCED_TEXT_EFFECTS
               for el in overlay.get("elements", []))


def _overlay_pass(
    renderer: MixRenderer, base_file: str, overlay: dict, out_file: str,
    runner: Callable[..., Any], log_path: str | None,
) -> None:
    """Draw the text tracks over the base — MoviePy for advanced effects, else drawtext."""
    used = False
    if _has_advanced_text(overlay):
        print("[sample] drawing animated text tracks (MoviePy)…", flush=True)
        try:
            render_moviepy_overlay(base_file, overlay, out_file, canvas=renderer._canvas,
                                   fps=renderer._fps, ffmpeg_exe=renderer._ffmpeg.exe())
            used = Path(out_file).exists()
        except Exception as exc:  # noqa: BLE001 - degrade to drawtext on any MoviePy error
            print(f"[sample] MoviePy text failed ({exc}); falling back to drawtext.", flush=True)
    if not used:
        print("[sample] drawing title/subtitle tracks…", flush=True)
        command = build_overlay_command(renderer, base_file, overlay, out_file)
        if command is not None:
            with _log_handle(log_path) as log:
                runner(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log).wait()
    if not Path(out_file).exists():  # nothing drawn -> keep the base
        shutil.copyfile(base_file, out_file)


@contextlib.contextmanager
def _log_handle(log_path: str | None):  # type: ignore[no-untyped-def]
    """Yield an append handle on ``log_path`` (or DEVNULL when unset)."""
    if log_path:
        handle = open(log_path, "a", encoding="utf-8")  # noqa: SIM115
        try:
            yield handle
        finally:
            handle.close()
    else:
        yield subprocess.DEVNULL


def stream_samples(
    segments: list[MixSegment],
    *,
    crossfade: float,
    sample_prep: SamplePrep,
    renderer: MixRenderer,
    runner: Callable[..., Any],
    vlc_binary: str | None = None,
    log_path: str | None = None,
    leading_path: str | None = None,
    leading_kind: str = "none",
    timeline: bool = False,
    dissolve: float = 0.0,
    overlay: dict | None = None,
) -> None:
    """Prep clips to small ``.ts``, render ONE mix FILE, then open it in VLC.

    A real file (not a live ``vlc -`` pipe) means VLC **auto-plays** it and the
    user can **replay/seek** — a piped stream is one-shot, un-seekable, and never
    restarts (the "can't open the video" error on replay). The mix file lives in
    the temp dir for the whole VLC session and is removed once VLC is closed.
    """
    tmp_dir = tempfile.mkdtemp(prefix="ytdl_sample_")
    try:
        prepared = _prepare_all(segments, sample_prep, tmp_dir)
        # Timeline overlays place each clip independently, so a single clip is valid;
        # the sequential xfade needs at least two clips to cross-fade.
        if len(prepared) < (1 if timeline else 2):
            print("[sample] not enough playable clips — nothing to show.", flush=True)
            return
        out_file = str(Path(tmp_dir) / "mix.mp4")
        # With overlay tracks, render the visual base to a tmp file, then draw the
        # title/subtitle text over it in a light second pass -> out_file.
        base_file = str(Path(tmp_dir) / "base.mp4") if overlay else out_file
        command = render_command(
            renderer, prepared, base_file, crossfade=crossfade,
            leading_path=leading_path, leading_kind=leading_kind,
            timeline=timeline, tmp_dir=tmp_dir, dissolve=dissolve,
        )
        print("[sample] rendering the mix…", flush=True)
        with _log_handle(log_path) as log:
            runner(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log).wait()
        if overlay:
            _overlay_pass(renderer, base_file, overlay, out_file, runner, log_path)
        print(
            "[sample] opening VLC — it auto-plays and is replayable. Close VLC to finish.",
            flush=True,
        )
        with _log_handle(log_path) as log:
            runner(
                [vlc_binary or DEFAULT_VLC_BINARY, out_file], stdout=log, stderr=log
            ).wait()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
