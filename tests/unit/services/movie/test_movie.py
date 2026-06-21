"""Unit tests for the movie-agent tools: YouTube search + playlist builder."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from ytdl.services.movie.builder import build_movie_playlist, load_segments, to_seconds
from ytdl.services.movie.search import search_youtube


def test_to_seconds_parses_clock_and_numbers() -> None:
    assert to_seconds("01:02:03") == 3723
    assert to_seconds("02:05") == 125
    assert to_seconds(42) == 42.0
    assert to_seconds("30") == 30


def test_search_maps_entries_and_query() -> None:
    client = MagicMock()
    client.extract_info.return_value = {"entries": [
        {"title": "A", "id": "abc", "duration": 120, "channel": "C"},
        {"title": "B", "url": "https://youtu.be/x", "duration": None},
    ]}
    out = search_youtube(client, "cats", results=5)
    assert client.extract_info.call_args.args[0] == "ytsearch5:cats"
    assert out[0] == {"video_title": "A", "video_url": "https://youtu.be/abc",
                      "duration_seconds": 120, "channel": "C"}
    assert out[1]["duration_seconds"] == 0  # missing duration -> 0


def test_build_movie_playlist_orders_and_times(tmp_path) -> None:
    segs = [
        {"sequence_number": 2, "start_time": "00:00:10", "duration_seconds": 8},
        {"sequence_number": 1, "start_time": "00:01:00", "duration_seconds": 6},
    ]
    out = build_movie_playlist(segs, str(tmp_path))
    txt = (tmp_path / "movie.yaml").read_text(encoding="utf-8")
    assert out.endswith("movie.yaml")
    assert txt.index("seg_1.mp4") < txt.index("seg_2.mp4")  # ordered by sequence_number
    assert "start_time: 60.0" in txt and "play_time: 6" in txt
    assert "mix: { video: true, audio: true }" in txt  # no leading -> clips keep audio


def test_build_movie_with_leading_audio(tmp_path) -> None:
    out = build_movie_playlist(
        [{"sequence_number": 1, "start_time": 0, "duration_seconds": 5}],
        str(tmp_path), leading_audio="song.mp3", out_path=str(tmp_path / "m.yaml"),
    )
    from pathlib import Path
    txt = Path(out).read_text(encoding="utf-8")
    assert "audio: false" in txt and "leading: { kind: audio, file: 'song.mp3' }" in txt


def test_load_segments_validates(tmp_path) -> None:
    good = tmp_path / "s.json"
    good.write_text(json.dumps([{"sequence_number": 1}]), encoding="utf-8")
    assert load_segments(str(good)) == [{"sequence_number": 1}]
    bad = tmp_path / "b.json"
    bad.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        load_segments(str(bad))
