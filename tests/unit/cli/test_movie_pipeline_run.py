"""CLI-handler tests for the movie-pipeline helpers (--to-segments, --search -o)."""

from __future__ import annotations

import json
from argparse import Namespace
from unittest.mock import patch

from ytdl.cli.exits import EXIT_SUCCESS
from ytdl.cli.movie_run import run_search
from ytdl.cli.pipeline_run import run_to_segments


def test_to_segments_handler_writes_scaffold(tmp_path) -> None:
    cand = tmp_path / "c.json"
    cand.write_text(json.dumps([{"video_url": "u1", "duration_seconds": 100}]), encoding="utf-8")
    out = tmp_path / "segments.json"
    rc = run_to_segments(Namespace(to_segments=str(cand), output_dir=str(out)))
    assert rc == EXIT_SUCCESS
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data[0]["sequence_number"] == 1 and data[0]["video_url"] == "u1"


def test_search_o_writes_candidates_file(tmp_path) -> None:
    out = tmp_path / "cand.json"
    args = Namespace(search="cats", search_results=3, output_dir=str(out))
    with patch("ytdl.cli.movie_run.YoutubeDownloaderSDK") as sdk:
        sdk.return_value.search.return_value = [{"video_url": "u", "duration_seconds": 5}]
        rc = run_search(args)
    assert rc == EXIT_SUCCESS
    assert json.loads(out.read_text(encoding="utf-8"))[0]["video_url"] == "u"
