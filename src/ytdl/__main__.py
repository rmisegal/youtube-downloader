"""Enables `python -m ytdl`; delegates to the CLI entry point."""

from __future__ import annotations

import sys

from ytdl.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
