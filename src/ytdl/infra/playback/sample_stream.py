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

from ytdl.constants import LEADING_AUDIO, LEADING_VIDEO
from ytdl.infra.playback.concat import build_concat_command, is_contiguous
from ytdl.infra.playback.renderer import MixRenderer
from ytdl.infra.playback.stream_server import DEFAULT_VLC_BINARY
from ytdl.infra.playback.timeline import build_timeline_command, timeline_total
from ytdl.infra.playback.xfade import build_xfade_command
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


def _render_command(
    renderer: MixRenderer,
    prepared: list[MixSegment],
    out_file: str,
    *,
    crossfade: float,
    leading_path: str | None,
    leading_kind: str,
    timeline: bool,
    tmp_dir: str,
    dissolve: float = 0.0,
) -> list[str]:
    """Pick the render command: crossfade/concat (contiguous), overlay, leading, or xfade."""
    if timeline:
        total = timeline_total(prepared)
        lead = leading_path
        if leading_path and leading_kind == LEADING_AUDIO:
            lead = renderer.looped_leading(leading_path, total, crossfade, tmp_dir)
        if is_contiguous(prepared):
            # Crossfade mode -> soft cross-dissolves (slower re-encode, no black);
            # otherwise fast concat (video stream-copied, clean cuts).
            if dissolve > 0 and len(prepared) > 1:
                return build_xfade_command(
                    renderer, prepared, total=total, leading_path=lead,
                    leading_kind=leading_kind, dissolve=dissolve, crossfade=crossfade,
                    output_path=out_file,
                )
            return build_concat_command(
                renderer, prepared, total=total, leading_path=lead,
                leading_kind=leading_kind, crossfade=crossfade,
                output_path=out_file, tmp_dir=tmp_dir,
            )
        # An OVERLAPPING manual timeline needs the N-input overlay compositor.
        return build_timeline_command(
            renderer, prepared, total=total, leading_path=lead,
            leading_kind=leading_kind, crossfade=crossfade, output_path=out_file,
        )
    if leading_path and leading_kind in (LEADING_VIDEO, LEADING_AUDIO):
        lead = leading_path
        if leading_kind == LEADING_AUDIO:
            video_seconds = sum(s.play_seconds or 0.0 for s in prepared) - crossfade * (
                len(prepared) - 1
            )
            lead = renderer.looped_leading(
                leading_path, max(0.0, video_seconds), crossfade, tmp_dir
            )
        return renderer.build_leading_command(
            prepared, lead, leading_kind, out_file, crossfade=crossfade
        )
    return renderer.build_command(prepared, out_file, crossfade=crossfade)


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
        command = _render_command(
            renderer, prepared, out_file, crossfade=crossfade,
            leading_path=leading_path, leading_kind=leading_kind,
            timeline=timeline, tmp_dir=tmp_dir, dissolve=dissolve,
        )
        print("[sample] rendering the mix…", flush=True)
        with _log_handle(log_path) as log:
            runner(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log).wait()
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
