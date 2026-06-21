"""Unit tests for :class:`SamplePrep` (all subprocess/probe boundaries mocked)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from ytdl.services.mixer.sample_prep import SamplePrep
from ytdl.services.mixer.segment import MixSegment


def _ffmpeg() -> MagicMock:
    loc = MagicMock()
    loc.exe.return_value = "/fake/ffmpeg"
    return loc


def _prep(probe, runner=None, log_path=None) -> SamplePrep:
    return SamplePrep(
        ffmpeg=_ffmpeg(),
        runner=runner or MagicMock(return_value=SimpleNamespace(returncode=0)),
        probe_fn=probe,
        log_path=log_path,
    )


def test_command_uses_source_audio_when_present() -> None:
    prep = _prep(lambda *_a: (30.0, True))
    seg = MixSegment("clip.mp4", start=5.0, play_seconds=10.0)
    cmd = prep.build_command(seg, "out.ts", has_audio=True)
    assert "anullsrc" not in " ".join(cmd)
    assert "0:a:0" in cmd
    assert "1:a:0" not in cmd
    assert cmd[:8] == ["/fake/ffmpeg", "-nostdin", "-y", "-ss", "5.0", "-t", "10.0", "-i"]


def test_slow_motion_applies_setpts_and_grabs_more_source() -> None:
    prep = _prep(lambda *_a: (30.0, True))
    seg = MixSegment("clip.mp4", start=0.0, play_seconds=4.0, speed=0.5)  # slow-motion
    cmd = prep.build_command(seg, "out.ts", has_audio=True)
    joined = " ".join(cmd)
    assert "setpts=PTS/0.5" in joined          # slows the motion
    assert "-t 2.0 -i" in joined               # grabs play*speed of source...
    assert cmd[-4:-1] == ["-t", "4.0", "-f"] or "-t 4.0" in joined  # ...output stays the slot


def test_normal_speed_has_no_setpts() -> None:
    prep = _prep(lambda *_a: (30.0, True))
    cmd = prep.build_command(MixSegment("clip.mp4", play_seconds=6.0), "out.ts", has_audio=True)
    assert "setpts" not in " ".join(cmd)


def test_command_synthesizes_silence_when_no_audio() -> None:
    prep = _prep(lambda *_a: (30.0, False))
    seg = MixSegment("clip.mp4", start=0.0, play_seconds=8.0)
    cmd = prep.build_command(seg, "out.ts", has_audio=False)
    joined = " ".join(cmd)
    assert "anullsrc=r=48000:cl=stereo" in joined
    assert "1:a:0" in cmd
    assert "-f" in cmd and "lavfi" in cmd


def test_command_normalizes_to_720p_h264_mpegts() -> None:
    prep = _prep(lambda *_a: (30.0, True))
    seg = MixSegment("clip.mp4", start=0.0, play_seconds=4.0)
    cmd = prep.build_command(seg, "out.ts", has_audio=True)
    joined = " ".join(cmd)
    assert "-c:v" in cmd and "libx264" in cmd
    assert "-preset" in cmd and "ultrafast" in cmd
    assert "scale=1280:720:force_original_aspect_ratio=decrease" in joined
    assert "pad=1280:720" in joined and "fps=30" in joined
    assert cmd[-3:] == ["-f", "mpegts", "out.ts"]


def test_image_command_loops_image_and_animates_with_silent_audio() -> None:
    prep = _prep(lambda *_a: (0.0, False))
    seg = MixSegment("cover.jpg", play_seconds=6.0, kind="image", transition="zoomin")
    cmd = prep.build_command(seg, "out.ts", has_audio=False)
    joined = " ".join(cmd)
    assert "-loop" in cmd and cmd[cmd.index("-loop") + 1] == "1"
    assert "-ss" not in cmd  # images are not seeked
    # The image input must NOT carry a -t (that explodes zoompan); -loop 1 -> -i.
    assert cmd[cmd.index("-loop") + 2] == "-i"
    # The output IS bounded: a -t appears AFTER the image input (output duration).
    img_i = cmd.index(seg.path)
    assert "-t" in cmd[img_i:]
    assert "anullsrc=r=48000:cl=stereo" in joined  # synthesized silent audio
    assert "zoompan=" in joined  # the per-image animation
    assert cmd[-3:] == ["-f", "mpegts", "out.ts"]


def test_prepare_image_skips_probe(monkeypatch) -> None:
    monkeypatch.setattr("ytdl.services.mixer.sample_prep.os.path.exists", lambda _p: True)
    probe = MagicMock(side_effect=AssertionError("must not probe an image"))
    runner = MagicMock(return_value=SimpleNamespace(returncode=0))
    prep = _prep(probe, runner=runner)
    seg = MixSegment("pic.png", play_seconds=5.0, kind="image", transition="fade")
    assert prep.prepare(seg, "out.ts") is True
    probe.assert_not_called()


def test_prepare_returns_true_on_success(monkeypatch) -> None:
    monkeypatch.setattr("ytdl.services.mixer.sample_prep.os.path.exists", lambda _p: True)
    runner = MagicMock(return_value=SimpleNamespace(returncode=0))
    prep = _prep(lambda *_a: (10.0, True), runner=runner)
    assert prep.prepare(MixSegment("a.mp4", play_seconds=5.0), "out.ts") is True
    runner.assert_called_once()


def test_prepare_returns_false_on_nonzero_rc(monkeypatch) -> None:
    monkeypatch.setattr("ytdl.services.mixer.sample_prep.os.path.exists", lambda _p: True)
    runner = MagicMock(return_value=SimpleNamespace(returncode=1))
    prep = _prep(lambda *_a: (10.0, True), runner=runner)
    assert prep.prepare(MixSegment("a.mp4", play_seconds=5.0), "out.ts") is False


def test_prepare_returns_false_when_output_missing(monkeypatch) -> None:
    monkeypatch.setattr("ytdl.services.mixer.sample_prep.os.path.exists", lambda _p: False)
    runner = MagicMock(return_value=SimpleNamespace(returncode=0))
    prep = _prep(lambda *_a: (10.0, True), runner=runner)
    assert prep.prepare(MixSegment("a.mp4", play_seconds=5.0), "out.ts") is False


def test_prepare_swallows_subprocess_errors() -> None:
    def boom(*_a, **_k):
        raise OSError("ffmpeg crashed")

    prep = _prep(lambda *_a: (10.0, True), runner=boom)
    assert prep.prepare(MixSegment("a.mp4", play_seconds=5.0), "out.ts") is False


def test_prepare_skips_on_timeout() -> None:
    import subprocess

    def slow(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=1)

    prep = _prep(lambda *_a: (10.0, True), runner=slow)
    assert prep.prepare(MixSegment("a.mp4", play_seconds=5.0), "out.ts") is False


def test_run_detaches_stdin_and_passes_timeout() -> None:
    import subprocess
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    runner = MagicMock(return_value=SimpleNamespace(returncode=0))
    prep = _prep(lambda *_a: (10.0, True), runner=runner)
    prep._run(["/fake/ffmpeg", "-i", "a.mp4"])
    assert runner.call_args.kwargs["stdin"] is subprocess.DEVNULL
    assert "timeout" in runner.call_args.kwargs
