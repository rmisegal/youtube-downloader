"""``SamplePrep`` — normalize ONE clip's sample to a small 720p H.264 ``.ts``.

Heavy clips (4K AV1, mixed/absent audio) can't be xfaded in one giant FFmpeg
graph. This prepares each clip's sample SEQUENTIALLY (the only heavy step) to a
small uniform ``.ts``: scale/pad to a common canvas, synthesize silent audio
when the source has none, and SKIP (return ``False``) any clip whose prep fails.
The verified per-clip recipe is wired faithfully; stderr goes to a log handle.
"""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Callable
from typing import Any

from ytdl.constants import MEMBER_IMAGE
from ytdl.infra.ffmpeg import FfmpegLocator
from ytdl.infra.playback.duration import probe_media
from ytdl.infra.playback.transitions import image_vfilter, resolve
from ytdl.services.mixer.segment import MixSegment

_LOGGER = logging.getLogger("ytdl.sample_prep")


class SamplePrep:
    """Prepare a clip's sample to a small normalized 720p H.264 ``.ts``."""

    def __init__(
        self,
        config: Any = None,
        ffmpeg: FfmpegLocator | None = None,
        runner: Callable[..., Any] = subprocess.run,
        log_path: str | None = None,
        probe_fn: Callable[..., tuple[float, bool]] = probe_media,
    ) -> None:
        self._ffmpeg = ffmpeg or FfmpegLocator()
        self._runner = runner
        self._log_path = log_path
        self._probe_fn = probe_fn
        get = config.get if config is not None else (lambda _k, default=None: default)
        self._width = get("render.width", 1280)
        self._height = get("render.height", 720)
        self._fps = get("render.fps", 30)
        self._preset = get("render.video_preset", "ultrafast")
        self._audio_codec = get("render.audio_codec", "aac")
        # Per-clip safety cap so one pathological file can never hang the run.
        self._timeout = get("render.prep_timeout_seconds", 120)

    def _vfilter(self) -> str:
        """The verified scale/pad/sar/fps/format chain to the common canvas."""
        w, h = self._width, self._height
        return (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={self._fps},format=yuv420p"
        )

    def build_command(
        self, segment: MixSegment, out_path: str, has_audio: bool
    ) -> list[str]:
        """Build the verified per-clip prep command (synthesize silence if needed)."""
        if segment.kind == MEMBER_IMAGE:
            return self._image_command(segment, out_path)
        play = segment.play_seconds or 0
        # ``-nostdin``: never read the inherited console — otherwise ffmpeg blocks
        # forever waiting on stdin and the whole sample run appears to hang.
        cmd = [
            self._ffmpeg.exe(), "-nostdin", "-y",
            "-ss", str(segment.start), "-t", str(play), "-i", segment.path,
        ]
        if has_audio:
            audio_map = "0:a:0"
        else:
            cmd += ["-f", "lavfi", "-t", str(play), "-i", "anullsrc=r=48000:cl=stereo"]
            audio_map = "1:a:0"
        cmd += [
            "-map", "0:v:0", "-map", audio_map,
            "-vf", self._vfilter(),
            "-c:v", "libx264", "-preset", self._preset,
            "-c:a", self._audio_codec,
            "-f", "mpegts", str(out_path),
        ]
        return cmd

    def _image_command(self, segment: MixSegment, out_path: str) -> list[str]:
        """Prep a still image: loop it, animate via the transition, add silent audio.

        Reuses the silent-audio (``anullsrc``) pattern so an image becomes a uniform
        ``.ts`` like any clip; the per-image animation comes from
        :mod:`ytdl.infra.playback.transitions` (``random`` by default).
        """
        play = segment.play_seconds or 0
        transition = resolve(segment.transition, segment.direction)
        vfilter = image_vfilter(transition, play, (self._width, self._height), self._fps)
        # CRITICAL: bound the OUTPUT with ``-t`` (after the inputs), NOT the image
        # input. ``zoompan`` emits ``d`` frames per input frame; an input-side ``-t``
        # on a looped image multiplies into tens of thousands of frames and the prep
        # hangs on real (high-res) photos. Output ``-t`` caps it at ``play*fps`` frames.
        return [
            self._ffmpeg.exe(), "-nostdin", "-y",
            "-loop", "1", "-i", segment.path,
            "-f", "lavfi", "-t", str(play), "-i", "anullsrc=r=48000:cl=stereo",
            "-map", "0:v:0", "-map", "1:a:0",
            "-vf", vfilter,
            "-t", str(play),
            "-c:v", "libx264", "-preset", self._preset,
            "-c:a", self._audio_codec,
            "-f", "mpegts", str(out_path),
        ]

    def prepare(self, segment: MixSegment, out_path: str) -> bool:
        """Prep ``segment`` to ``out_path``; return ``True`` on success, else skip.

        Probes audio presence, runs the verified command with stderr captured to
        the log (or DEVNULL). Never raises: subprocess errors are logged and
        reported as ``False`` so the caller simply skips that clip.
        """
        try:
            if segment.kind == MEMBER_IMAGE:
                command = self.build_command(segment, out_path, has_audio=False)
            else:
                _duration, has_audio = self._probe_fn(segment.path, self._ffmpeg.exe())
                command = self.build_command(segment, out_path, has_audio)
            code = self._run(command)
        except (OSError, subprocess.SubprocessError) as exc:
            _LOGGER.error("prep failed for %s: %s", segment.path, exc)
            return False
        if code == 0 and os.path.exists(out_path):
            return True
        _LOGGER.error("prep skipped %s (rc=%s)", segment.path, code)
        return False

    def _run(self, command: list[str]) -> int:
        """Run ``command`` with stdin detached + a timeout; stderr to log/DEVNULL.

        ``stdin=DEVNULL`` is the load-bearing fix: ffmpeg with an inherited console
        stdin blocks indefinitely. The ``timeout`` is a belt-and-suspenders cap.
        """
        try:
            if self._log_path:
                with open(self._log_path, "a", encoding="utf-8") as handle:
                    result = self._runner(
                        command, stdin=subprocess.DEVNULL, stderr=handle, timeout=self._timeout
                    )
            else:
                result = self._runner(
                    command, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=self._timeout,
                )
        except subprocess.TimeoutExpired:
            _LOGGER.error("prep timed out after %ss: %s", self._timeout, command[-1])
            return 124
        return getattr(result, "returncode", 0)
