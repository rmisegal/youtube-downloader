"""``Sampler`` — random mid-band segment builder for ``--sample-play`` (PRD-playlist §3).

Probes each clip's duration, seeks to a random point in the configured mid-band,
and emits ``list[MixSegment]`` (looping the folder by default).

# Implemented in Phase 5.
"""

from __future__ import annotations
