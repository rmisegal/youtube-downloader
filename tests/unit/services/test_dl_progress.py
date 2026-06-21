"""Unit tests for the download progress hook."""

from __future__ import annotations

import io

from ytdl.services.dl_progress import make_progress_hook


def test_prints_progress_lines_and_finish() -> None:
    out = io.StringIO()
    hook = make_progress_hook(out)
    for done in (0, 1000, 3000, 5000, 7000, 9000, 10000):
        hook({"status": "downloading", "downloaded_bytes": done,
              "total_bytes": 10000, "filename": "C:/x/a.mp4"})
    hook({"status": "finished", "filename": "C:/x/a.mp4", "total_bytes": 10000})
    text = out.getvalue()
    assert "a.mp4" in text and "done" in text
    assert text.count("[download]") >= 3  # throttled to ~every 20%


def test_ignores_non_downloading_status() -> None:
    out = io.StringIO()
    make_progress_hook(out)({"status": "processing"})
    assert out.getvalue() == ""
