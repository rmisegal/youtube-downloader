"""Entry shim so `python -m ytdl` / `python src/main.py` invoke the CLI.

This file holds no business logic; it delegates to :func:`ytdl.cli.main.main`.
It is omitted from coverage (see pyproject ``[tool.coverage.run]``).
"""

from __future__ import annotations

import sys


def _run() -> int:
    from ytdl.cli.main import main

    return main()


if __name__ == "__main__":
    sys.exit(_run())
