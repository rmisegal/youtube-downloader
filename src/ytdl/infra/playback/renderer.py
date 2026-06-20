"""``MixRenderer`` — the "save" engine (PRD-playlist §6).

Builds a single continuous FFmpeg graph over N trimmed inputs (xfade + acrossfade
with cumulative offsets) and writes one file; handles leading-video (``-an``) and
leading-audio (``-vn``) variants. Reuses ``FfmpegLocator`` + ``probe_duration``.

# Implemented in Phase 4.
"""

from __future__ import annotations
