"""CLI entry point.

Phases 1-3 establish the foundation only; the full argparse interface and SDK
delegation are implemented in Phase 7. This placeholder keeps the
``python -m ytdl`` entry wiring importable and returns a clear not-ready signal.
"""

from __future__ import annotations

import sys

# Reserved, non-zero exit code for "CLI not yet implemented" (Phase 7 supersedes).
EXIT_NOT_IMPLEMENTED: int = 70


def main(argv: list[str] | None = None) -> int:
    """Temporary entry point; replaced by the full CLI in Phase 7."""
    del argv  # unused until Phase 7
    print(
        "ytdl CLI is not yet implemented (Phase 7). "
        "The package foundation (config, constants) is in place.",
        file=sys.stderr,
    )
    return EXIT_NOT_IMPLEMENTED
