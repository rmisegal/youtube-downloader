"""Deterministic CLI exit codes (PRD §3.3, PRD-mixer §, PRD-playlist §9).

Shared by :mod:`ytdl.cli.main` and :mod:`ytdl.cli.run` so the handlers and the
entry module agree on the codes without a circular import.
"""

from __future__ import annotations

EXIT_SUCCESS: int = 0
EXIT_GENERIC_ERROR: int = 1
EXIT_INVALID_URL: int = 2
EXIT_NETWORK_ERROR: int = 3
EXIT_UNSUPPORTED: int = 4
EXIT_CONFIG_VERSION: int = 5
EXIT_RATE_LIMIT: int = 6  # configured quota hit or YouTube HTTP 429
EXIT_PLAYBACK_DEP: int = 7  # VLC / playback dependency missing
EXIT_PLAYLIST: int = 8  # invalid/malformed playlist YAML (PlaylistError)
EXIT_ANALYSIS: int = 9  # audio analysis failed (AudioAnalysisError)
EXIT_USAGE: int = 2  # argparse/missing-url/missing-dir usage error
