"""Engine adapters presenting the interface :class:`MixerService` calls.

`MixerService` invokes ``stream_server.run(...)`` (Option 1) and
``matrix.play_sequence(timing...)`` (Option 2) with per-call timing but no
durations. These thin adapters wrap the Phase-B engines (:class:`StreamServer`,
:class:`LibVlcPlayerMatrix`), probe each source's duration (so the default
mix-out point = ``duration − crossfade``), and configure the underlying engine.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ytdl.infra.ffmpeg import FfmpegLocator
from ytdl.infra.playback.duration import probe_duration
from ytdl.infra.playback.option2_engine import Option2Engine
from ytdl.infra.playback.renderer import MixRenderer
from ytdl.infra.playback.sample_stream import stream_samples
from ytdl.infra.playback.stream_server import StreamServer
from ytdl.services.mixer.sample_prep import SamplePrep
from ytdl.services.mixer.segment import MixSegment

# Re-exported so callers keep importing both engines from this module.
__all__ = ["Option1Engine", "Option2Engine"]


class Option1Engine:
    """Option 1 adapter: stream consecutive crossfade pairs through VLC."""

    def __init__(
        self,
        stream_server: StreamServer | None = None,
        ffmpeg: FfmpegLocator | None = None,
        duration_fn: Callable[..., float] = probe_duration,
        renderer: MixRenderer | None = None,
        runner: Callable[..., Any] = subprocess.Popen,
        sample_prep: SamplePrep | None = None,
        log_path: str | None = None,
    ) -> None:
        self._ffmpeg = ffmpeg or FfmpegLocator()
        self._stream = stream_server or StreamServer(self._ffmpeg)
        self._duration_fn = duration_fn
        self._renderer = renderer or MixRenderer(self._ffmpeg)
        self._runner = runner
        self._sample_prep = sample_prep or SamplePrep(ffmpeg=self._ffmpeg, log_path=log_path)
        self._log_path = log_path

    def run(
        self,
        tracks: Sequence[Path | str],
        *,
        crossfade: float,
        source_mix_time: float | None,
        target_start_time: float | None,
        vlc_binary: str | None = None,
    ) -> None:
        """Stream each consecutive (source → target) pair with a true crossfade."""
        for index in range(len(tracks) - 1):
            source = str(tracks[index])
            duration = self._duration_fn(source, self._ffmpeg.exe())
            self._stream.stream_pair(
                source,
                str(tracks[index + 1]),
                crossfade=crossfade,
                source_duration=duration,
                source_mix_time=source_mix_time,
                target_start_time=target_start_time or 0.0,
                vlc_binary=vlc_binary,
            )

    def run_segments(
        self,
        segments: list[MixSegment],
        *,
        crossfade: float,
        vlc_binary: str | None = None,
        leading_path: str | None = None,
        leading_kind: str = "none",
        timeline: bool = False,
        dissolve: float = 0.0,
    ) -> None:
        """Prep each clip's sample to a small ``.ts`` ONE AT A TIME, then stitch.

        Each clip is normalized to a small 720p ``.ts`` sequentially (synthesizing
        silent audio when it has none, SKIPPING any clip whose prep fails); the
        small uniform clips are xfade-stitched into ONE mix file opened in ONE VLC.
        With ``leading_kind`` (``audio``/``video``) the leading track supplies the
        soundtrack/master picture — same flow, shared with ``--sample-play``.
        See :func:`ytdl.infra.playback.sample_stream.stream_samples`.
        """
        stream_samples(
            list(segments),
            crossfade=crossfade,
            sample_prep=self._sample_prep,
            renderer=self._renderer,
            runner=self._runner,
            vlc_binary=vlc_binary,
            log_path=self._log_path,
            leading_path=leading_path,
            leading_kind=leading_kind,
            timeline=timeline,
            dissolve=dissolve,
        )
