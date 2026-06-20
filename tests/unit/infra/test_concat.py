"""Unit tests for the contiguity check + concat command builder."""

from __future__ import annotations

from unittest.mock import MagicMock

from ytdl.infra.playback.concat import build_concat_command, is_contiguous
from ytdl.services.mixer.segment import MixSegment


def _seg(at, dur, path="c.ts") -> MixSegment:
    return MixSegment(path=path, start=0.0, play_seconds=dur, at=at)


def test_contiguous_true_for_back_to_back() -> None:
    assert is_contiguous([_seg(0, 2, "a"), _seg(2, 3, "b"), _seg(5, 1, "c")]) is True


def test_contiguous_false_for_overlap() -> None:
    assert is_contiguous([_seg(0, 3, "a"), _seg(2, 3, "b")]) is False


def test_contiguous_false_for_gap() -> None:
    assert is_contiguous([_seg(0, 2, "a"), _seg(5, 2, "b")]) is False


def test_contiguous_false_for_leading_gap() -> None:
    assert is_contiguous([_seg(3, 2, "a"), _seg(5, 2, "b")]) is False


def test_contiguous_false_when_any_unplaced() -> None:
    assert is_contiguous([_seg(0, 2, "a"), MixSegment(path="b", play_seconds=2)]) is False


def test_build_concat_command_with_audio(tmp_path) -> None:
    renderer = MagicMock()
    renderer._ffmpeg.exe.return_value = "/ff"
    (tmp_path / "a.ts").write_bytes(b"x")
    (tmp_path / "b.ts").write_bytes(b"x")
    segs = [_seg(0, 2, str(tmp_path / "a.ts")), _seg(2, 2, str(tmp_path / "b.ts"))]
    cmd = build_concat_command(
        renderer, segs, total=4.0, leading_path="song.wav", leading_kind="audio",
        crossfade=2, output_path="out.mp4", tmp_dir=str(tmp_path),
    )
    joined = " ".join(cmd)
    assert "concat" in cmd and "-safe" in cmd and "copy" in cmd  # video stream-copied
    assert cmd[-1] == "out.mp4"
    assert "[aout]" in joined and "afade" in joined  # leading audio faded
    listing = (tmp_path / "concat.txt").read_text(encoding="utf-8")
    assert "a.ts" in listing and "b.ts" in listing


def test_build_concat_command_no_audio(tmp_path) -> None:
    renderer = MagicMock()
    renderer._ffmpeg.exe.return_value = "/ff"
    (tmp_path / "a.ts").write_bytes(b"x")
    cmd = build_concat_command(
        renderer, [_seg(0, 2, str(tmp_path / "a.ts"))], total=2.0, leading_path=None,
        leading_kind="none", crossfade=2, output_path="out.mp4", tmp_dir=str(tmp_path),
    )
    assert "[aout]" not in " ".join(cmd) and "copy" in cmd
