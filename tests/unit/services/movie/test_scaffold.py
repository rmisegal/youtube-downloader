"""Unit tests for the candidates → segments scaffold."""

from __future__ import annotations

import json

import pytest

from ytdl.services.movie.scaffold import (
    candidates_to_segments,
    load_candidates,
    write_segments,
)


def test_candidates_become_ordered_segments() -> None:
    cands = [
        {"video_title": "A", "video_url": "https://youtu.be/a", "duration_seconds": 200},
        {"video_title": "B", "video_url": "https://youtu.be/b", "duration_seconds": 90},
    ]
    segs = candidates_to_segments(cands)
    assert [s["sequence_number"] for s in segs] == [1, 2]
    assert segs[0]["video_url"] == "https://youtu.be/a"
    # full-video duration is NOT used as the clip length — a short editable default is
    assert segs[0]["duration_seconds"] == 6
    assert segs[0]["start_time"] == "00:00:00"


def test_load_candidates_validates(tmp_path) -> None:
    good = tmp_path / "c.json"
    good.write_text(json.dumps([{"video_url": "u"}]), encoding="utf-8")
    assert load_candidates(str(good)) == [{"video_url": "u"}]
    bad = tmp_path / "b.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        load_candidates(str(bad))


def test_write_segments_roundtrips(tmp_path) -> None:
    from pathlib import Path
    out = write_segments([{"sequence_number": 1}], str(tmp_path / "sub" / "segments.json"))
    assert json.loads(Path(out).read_text(encoding="utf-8")) == [{"sequence_number": 1}]
