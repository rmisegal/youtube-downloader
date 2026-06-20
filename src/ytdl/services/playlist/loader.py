"""YAML playlist loader: parse + validate -> model, build ``MixSegment``s.

Uses ``yaml.safe_load``; raises ``PlaylistError`` on malformed/invalid input
(PRD-playlist §5.3, exit code 8).

# Implemented in Phase 5.
"""

from __future__ import annotations
