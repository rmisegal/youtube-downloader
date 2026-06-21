"""CLI handlers for the movie-pipeline (wizard → make-movie) and the segments scaffold.

Kept out of :mod:`ytdl.cli.movie_run` so each file stays ≤150 lines (Rule 8). Each
handler delegates to the SDK (Rule 1). For now: ``--to-segments`` scaffolds an editable
segments JSON from ``--search`` candidates; the full ``--make-movie`` pipeline + wizard
handlers land in later phases.
"""

from __future__ import annotations

import logging

from ytdl.cli.exits import EXIT_GENERIC_ERROR, EXIT_SUCCESS, EXIT_USAGE
from ytdl.cli.run import _fail
from ytdl.sdk.sdk import YoutubeDownloaderSDK

_LOGGER = logging.getLogger("ytdl.cli")


def run_to_segments(args) -> int:  # noqa: ANN001 - argparse.Namespace
    """Scaffold an editable segments JSON from a ``--search`` candidates file."""
    out = args.output_dir or "segments.json"
    _LOGGER.info("phase=to-segments candidates=%s out=%s", args.to_segments, out)
    try:
        path = YoutubeDownloaderSDK().to_segments(args.to_segments, out)
    except (OSError, ValueError) as exc:
        return _fail("Could not read the candidates JSON", exc, EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        return _fail("Unexpected error", exc, EXIT_GENERIC_ERROR)
    print(f"Scaffolded segments -> {path}")
    print("Edit start_time/duration per scene, then: --fetch-movie then --build-movie")
    return EXIT_SUCCESS
