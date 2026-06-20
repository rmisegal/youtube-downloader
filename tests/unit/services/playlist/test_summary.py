"""Unit tests for ``compute_summary`` (PRD-playlist §5.2/§5.3 step 7).

All boundaries injected: ``duration_fn`` and ``size_fn`` are fakes, so no real
files or FFmpeg are touched.
"""

from __future__ import annotations

from ytdl.services.mixer.segment import MixSegment
from ytdl.services.playlist.summary import compute_summary


def _seg(path: str, **kw: object) -> MixSegment:
    return MixSegment(path=path, **kw)  # type: ignore[arg-type]


def _no_probe(*_a: object, **_k: object) -> float:
    raise AssertionError("duration_fn should not be called")


def _fixed_size(_path: str) -> int:
    return 100


def test_total_length_subtracts_crossfade_overlap() -> None:
    segs = [_seg(f"c{i}.mp4", play_seconds=10.0) for i in range(3)]
    out = compute_summary(segs, crossfade=2.0, duration_fn=_no_probe, size_fn=_fixed_size)
    # 3 * 10 - (3-1) * 2 = 30 - 4 = 26
    assert out["total_length_seconds"] == 26.0


def test_none_play_seconds_uses_probed_duration() -> None:
    segs = [_seg("a.mp4", play_seconds=10.0), _seg("b.mp4", play_seconds=None)]

    def fake_duration(path: str, _exe: str) -> float:
        return 7.5 if path == "b.mp4" else 0.0

    out = compute_summary(
        segs, crossfade=0.0, duration_fn=fake_duration, size_fn=_fixed_size
    )
    assert out["total_length_seconds"] == 17.5


def test_total_size_sums_size_fn_over_members() -> None:
    sizes = {"a.mp4": 111, "b.mp4": 222}
    segs = [_seg("a.mp4", play_seconds=1.0), _seg("b.mp4", play_seconds=1.0)]
    out = compute_summary(
        segs, crossfade=0.0, duration_fn=_no_probe, size_fn=lambda p: sizes[p]
    )
    assert out["total_file_size_bytes"] == 333


def test_total_size_counts_each_unique_file_once() -> None:
    segs = [_seg("a.mp4", play_seconds=1.0), _seg("a.mp4", start=5.0, play_seconds=1.0)]
    out = compute_summary(
        segs, crossfade=0.0, duration_fn=_no_probe, size_fn=lambda _p: 50
    )
    assert out["total_file_size_bytes"] == 50


def test_resolution_all_max_reports_max() -> None:
    segs = [_seg("a.mp4", play_seconds=1.0), _seg("b.mp4", play_seconds=1.0)]
    out = compute_summary(segs, crossfade=0.0, duration_fn=_no_probe, size_fn=_fixed_size)
    assert out["resolution"] == "max"


def test_resolution_concrete_wxh_is_reported() -> None:
    segs = [
        _seg("a.mp4", play_seconds=1.0, resolution="max"),
        _seg("b.mp4", play_seconds=1.0, resolution="1280x720"),
    ]
    out = compute_summary(segs, crossfade=0.0, duration_fn=_no_probe, size_fn=_fixed_size)
    assert out["resolution"] == "1280x720"


def test_resolution_reports_tallest_concrete() -> None:
    segs = [
        _seg("a.mp4", play_seconds=1.0, resolution="640x360"),
        _seg("b.mp4", play_seconds=1.0, resolution="1920x1080"),
    ]
    out = compute_summary(segs, crossfade=0.0, duration_fn=_no_probe, size_fn=_fixed_size)
    assert out["resolution"] == "1920x1080"


def test_members_lists_basenames_in_order() -> None:
    segs = [
        _seg("C:/videos/intro.mp4", play_seconds=1.0),
        _seg("C:/other/clip2.mkv", play_seconds=1.0),
    ]
    out = compute_summary(segs, crossfade=0.0, duration_fn=_no_probe, size_fn=_fixed_size)
    assert out["members"] == ["intro.mp4", "clip2.mkv"]


def test_length_floored_at_zero_for_degenerate_input() -> None:
    # Huge crossfade vs tiny play windows -> would go negative; floored at 0.0.
    segs = [_seg("a.mp4", play_seconds=1.0), _seg("b.mp4", play_seconds=1.0)]
    out = compute_summary(
        segs, crossfade=100.0, duration_fn=_no_probe, size_fn=_fixed_size
    )
    assert out["total_length_seconds"] == 0.0


def test_returns_exactly_four_keys() -> None:
    segs = [_seg("a.mp4", play_seconds=1.0)]
    out = compute_summary(segs, crossfade=0.0, duration_fn=_no_probe, size_fn=_fixed_size)
    assert set(out) == {
        "total_length_seconds",
        "total_file_size_bytes",
        "resolution",
        "members",
    }


def test_non_numeric_resolution_tail_is_ignored() -> None:
    # A malformed "WxH" whose height is non-numeric -> height 0 -> falls back to "max".
    segs = [_seg("a.mp4", play_seconds=1.0, resolution="1280xHD")]
    out = compute_summary(segs, crossfade=0.0, duration_fn=_no_probe, size_fn=_fixed_size)
    assert out["resolution"] == "max"


def test_empty_segments_is_safe() -> None:
    out = compute_summary([], crossfade=2.0, duration_fn=_no_probe, size_fn=_fixed_size)
    assert out == {
        "total_length_seconds": 0.0,
        "total_file_size_bytes": 0,
        "resolution": "max",
        "members": [],
    }
