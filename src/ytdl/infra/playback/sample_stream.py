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

from ytdl.infra.playback.renderer import MixRenderer
from ytdl.infra.playback.stream_server import DEFAULT_VLC_BINARY
from ytdl.services.mixer.sample_prep import SamplePrep
from ytdl.services.mixer.segment import MixSegment


def _prepare_all(
    segments: list[MixSegment], sample_prep: SamplePrep, tmp_dir: str
) -> list[MixSegment]:
    """Prep each segment sequentially; return the prepared (succeeded) clips."""
    prepared: list[MixSegment] = []
    for index, seg in enumerate(segments):
        out_path = str(Path(tmp_dir) / f"{index:02d}.ts")
        if sample_prep.prepare(seg, out_path):
            prepared.append(MixSegment(path=out_path, start=0.0, play_seconds=seg.play_seconds))
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


def stream_samples(
    segments: list[MixSegment],
    *,
    crossfade: float,
    sample_prep: SamplePrep,
    renderer: MixRenderer,
    runner: Callable[..., Any],
    vlc_binary: str | None = None,
    log_path: str | None = None,
) -> None:
    """Prep clips to small ``.ts``, then xfade-stitch them into one ``vlc -``."""
    tmp_dir = tempfile.mkdtemp(prefix="ytdl_sample_")
    try:
        prepared = _prepare_all(segments, sample_prep, tmp_dir)
        if len(prepared) < 2:
            return
        command = renderer.build_command(
            prepared, "pipe:1", crossfade=crossfade, container="mpegts"
        )
        with _log_handle(log_path) as log:
            ffmpeg = runner(command, stdout=subprocess.PIPE, stderr=log)
            vlc = runner(
                [vlc_binary or DEFAULT_VLC_BINARY, "-"],
                stdin=ffmpeg.stdout,
                stdout=log,
                stderr=log,
            )
            vlc.wait()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
