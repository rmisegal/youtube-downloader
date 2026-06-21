"""FETCH stage — download each scene's video to ``seg_<n>.mp4`` (dedup + resume).

A video that serves several scenes is downloaded **once** and copied to the other
scenes' file names; already-present files are skipped, so a re-run resumes. Failures
are recorded and the rest continue (the build can tolerate gaps).
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

DownloadFn = Callable[[str, str], Any]  # (url, dest_basename) → writes <dest_basename>.mp4


def fetch_segments(
    download_fn: DownloadFn, segments: list[dict[str, Any]], videos_dir: str,
) -> tuple[list[int], list[int]]:
    """Download every segment's video (dedup by URL); return (done, failed) seq lists."""
    vids = Path(videos_dir)
    vids.mkdir(parents=True, exist_ok=True)
    by_url: dict[str, Path] = {}
    done: list[int] = []
    failed: list[int] = []
    for seg in sorted(segments, key=lambda s: s.get("sequence_number", 0)):
        n = seg.get("sequence_number")
        url = seg.get("video_url", "")
        dest = vids / f"seg_{n}.mp4"
        if dest.exists():
            by_url.setdefault(url, dest)
            done.append(n)
            continue
        if url in by_url and by_url[url].exists():  # same video as an earlier scene → copy
            shutil.copyfile(by_url[url], dest)
            done.append(n)
            continue
        print(f"[fetch {len(done) + len(failed) + 1}/{len(segments)}] seg_{n}: {url}", flush=True)
        try:
            download_fn(url, f"seg_{n}")
            if dest.exists():
                by_url[url] = dest
            done.append(n)
        except Exception as exc:  # noqa: BLE001 - record + continue with the rest
            print(f"[fetch] seg_{n} FAILED: {exc}", flush=True)
            failed.append(n)
    return done, failed
