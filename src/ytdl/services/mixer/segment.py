"""``MixSegment`` value object — shared per-clip timing currency (PRD-playlist §2).

The sampler, ``--play-for-sec``, and YAML playlist members each produce
``list[MixSegment]``; engines and the ``MixRenderer`` consume them.

# Dataclass implemented in Phase 4.
"""

from __future__ import annotations
