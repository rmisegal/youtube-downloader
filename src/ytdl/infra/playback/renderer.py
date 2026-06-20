"""``MixRenderer`` — the "save" engine (PRD-playlist §6).

Builds a single continuous FFmpeg graph over N trimmed inputs (xfade + acrossfade
with cumulative offsets) and writes one file; handles leading-video (``-an``) and
leading-audio (``-vn``) variants. Reuses ``FfmpegLocator`` + ``probe_duration``.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ytdl.infra.ffmpeg import FfmpegLocator
from ytdl.infra.playback.duration import probe_duration
from ytdl.infra.playback.renderer_graph import (
    build_audio_graph,
    build_video_graph,
)
from ytdl.infra.playback.renderer_leading import leading_command
from ytdl.infra.playback.renderer_loop import build_loop_command, loop_copies
from ytdl.services.mixer.segment import MixSegment


def _fmt(value: float) -> str:
    """Format a time/duration compactly (no trailing ``.0``)."""
    return str(int(value)) if float(value).is_integer() else str(value)


class MixRenderer:
    """Render a ``list[MixSegment]`` into ONE file via a continuous FFmpeg graph."""

    def __init__(
        self,
        ffmpeg: FfmpegLocator | None = None,
        runner: Callable[..., Any] = subprocess.run,
        duration_fn: Callable[..., float] = probe_duration,
        config: Any = None,
        log_path: str | None = None,
    ) -> None:
        self._ffmpeg = ffmpeg or FfmpegLocator()
        self._runner = runner
        self._duration_fn = duration_fn
        self._log_path = log_path
        get = config.get if config is not None else (lambda _k, default=None: default)
        self._video_codec = get("render.video_codec", "libx264")
        self._audio_codec = get("render.audio_codec", "aac")
        self._container = get("render.container", "mp4")
        self._canvas = (get("render.width", 1280), get("render.height", 720))
        self._fps = get("render.fps", 30)
        self._preset = get("render.video_preset", "ultrafast")

    def _durations(self, segments: Sequence[MixSegment]) -> list[float]:
        """Resolve each segment's play window, probing when ``play_seconds`` is None."""
        out: list[float] = []
        for seg in segments:
            if seg.play_seconds is None:
                out.append(self._duration_fn(seg.path, self._ffmpeg.exe()))
            else:
                out.append(seg.play_seconds)
        return out

    def _inputs(self, segments: Sequence[MixSegment], durations: Sequence[float]) -> list[str]:
        """``-ss start -t play`` before each ``-i path`` (one input per segment)."""
        argv: list[str] = []
        for seg, play in zip(segments, durations, strict=True):
            argv += ["-ss", _fmt(seg.start), "-t", _fmt(play), "-i", seg.path]
        return argv

    def _codec_out(self, output_path: str, fmt: str | None = None) -> list[str]:
        """Codec flags (+ optional ``-f`` muxer) and the output target."""
        out = ["-c:v", self._video_codec, "-preset", self._preset, "-c:a", self._audio_codec]
        if fmt:
            out += ["-f", fmt]
        out.append(str(output_path))
        return out

    def build_command(
        self,
        segments: Sequence[MixSegment],
        output_path: str,
        *,
        crossfade: float,
        container: str | None = None,
    ) -> list[str]:
        """Full N-input xfade+acrossfade render command (no leading track).

        ``container`` forces an output muxer (e.g. ``"mpegts"`` with
        ``output_path="pipe:1"`` to stream into ``vlc -``).
        """
        durations = self._durations(segments)
        vsteps, vlabel = build_video_graph(segments, durations, crossfade, self._canvas, self._fps)
        asteps, alabel = build_audio_graph(segments, durations, crossfade)
        graph = ";".join(vsteps + asteps)
        return [
            self._ffmpeg.exe(),
            "-nostdin",
            "-y",
            *self._inputs(segments, durations),
            "-filter_complex",
            graph,
            "-map",
            f"[{vlabel}]",
            "-map",
            f"[{alabel}]",
            *self._codec_out(output_path, container),
        ]

    def build_leading_command(
        self,
        segments: Sequence[MixSegment],
        leading_path: str,
        leading_kind: str,
        output_path: str,
        *,
        crossfade: float,
    ) -> list[str]:
        """Render with a leading video (``-an``) or leading audio (``-vn``) master."""
        return leading_command(
            self, segments, leading_path, leading_kind, output_path, crossfade=crossfade
        )

    def render(
        self,
        segments: Sequence[MixSegment],
        target_folder: str,
        *,
        crossfade: float,
        leading_path: str | None = None,
        leading_kind: str = "none",
        name: str = "mix",
    ) -> str:
        """Build the appropriate command and run it via the injected runner."""
        output_path = str(Path(target_folder) / f"{name}.{self._container}")
        if leading_kind in ("video", "audio") and leading_path:
            command = self.build_leading_command(
                segments, leading_path, leading_kind, output_path, crossfade=crossfade
            )
        else:
            command = self.build_command(segments, output_path, crossfade=crossfade)
        self._run(command)
        return output_path

    def _run(self, command: list[str]) -> None:
        """Run an ffmpeg command (stdin detached) with stderr to log/DEVNULL."""
        if self._log_path:
            with open(self._log_path, "a", encoding="utf-8") as handle:
                self._runner(command, stdin=subprocess.DEVNULL, stderr=handle)
        else:
            self._runner(command, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def looped_leading(
        self, leading_path: str, video_seconds: float, crossfade: float, tmp_dir: str
    ) -> str:
        """Return a leading-audio path that covers ``video_seconds``.

        When the song is shorter than the video, pre-renders a crossfade-looped
        copy (clean dissolving seams) into ``tmp_dir`` and returns it; otherwise
        returns ``leading_path`` unchanged (no loop needed).
        """
        audio_seconds = self._duration_fn(leading_path, self._ffmpeg.exe())
        copies = loop_copies(audio_seconds, video_seconds, crossfade)
        if copies < 2:
            return leading_path
        out = str(Path(tmp_dir) / "leadloop.m4a")
        self._run(build_loop_command(self._ffmpeg.exe(), leading_path, copies, crossfade, out))
        return out if Path(out).is_file() else leading_path
