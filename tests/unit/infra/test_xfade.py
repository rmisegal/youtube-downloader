"""Unit tests for the crossfade (cross-dissolve) command builder + render routing."""

from __future__ import annotations

from unittest.mock import MagicMock

from ytdl.infra.playback.sample_stream import _render_command
from ytdl.infra.playback.xfade import build_xfade_command
from ytdl.services.mixer.segment import MixSegment


def _renderer() -> MagicMock:
    r = MagicMock()
    r._ffmpeg.exe.return_value = "/ff"
    r._codec_out.side_effect = lambda path: ["-c:v", "libx264", "-c:a", "aac", path]
    r.looped_leading.return_value = "lead.wav"
    return r


def _seg(at, dur, path="c.ts") -> MixSegment:
    return MixSegment(path=path, start=0.0, play_seconds=dur, at=at)


def test_xfade_command_dissolves_without_black() -> None:
    segs = [_seg(0, 2, "a.ts"), _seg(2, 3, "b.ts"), _seg(5, 1, "c.ts")]
    cmd = build_xfade_command(
        _renderer(), segs, total=6.0, leading_path="song.wav", leading_kind="audio",
        dissolve=0.5, crossfade=2.0, output_path="out.mp4",
    )
    joined = " ".join(cmd)
    assert "xfade=transition=fade" in joined  # a DISSOLVE, not fade-through-black
    assert "fade=t=in" not in joined  # no video fade-FROM-black (the audio afade is fine)
    assert "tpad=stop_mode=clone" in joined  # frozen tail keeps the total intact
    assert "[aout]" in joined and "afade" in joined  # leading audio mapped + faded
    assert cmd[-1] == "out.mp4"
    # offsets accumulate slot durations: first xfade at 2.0, second at 5.0.
    assert "offset=2" in joined and "offset=5" in joined


def test_render_routes_to_xfade_only_when_dissolve_set(tmp_path) -> None:
    prepared = [_seg(0, 2, "a.ts"), _seg(2, 2, "b.ts")]
    concat = _render_command(_renderer(), prepared, "o.mp4", crossfade=2,
                             leading_path="s.wav", leading_kind="audio",
                             timeline=True, tmp_dir=str(tmp_path), dissolve=0.0)
    assert "concat" in concat and "xfade=transition" not in " ".join(concat)
    xf = _render_command(_renderer(), prepared, "o.mp4", crossfade=2,
                         leading_path="s.wav", leading_kind="audio",
                         timeline=True, tmp_dir=str(tmp_path), dissolve=0.5)
    assert "xfade=transition=fade" in " ".join(xf)
