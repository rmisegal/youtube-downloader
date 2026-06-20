"""Parse user item-number selections like ``"1,3,5"`` or ``"2-4"``.

Shared by the playlist picker (`cli/playlist.py`, which wants the normalized
yt-dlp string form) and the video mixer (`services/mixer`, which wants concrete
1-based indices). Keeping it here avoids duplication and a services→cli import.
"""

from __future__ import annotations


def parse_selection(raw: str) -> str | None:
    """Normalize ``"1, 3 ,5 , 2-4"`` → ``"1,3,5,2-4"`` (yt-dlp ``playlist_items`` form).

    Keeps integers and ``a-b`` ranges; drops empty/invalid tokens; ``None`` if empty.
    """
    tokens = [p for p in raw.replace(" ", "").split(",") if p and (p.isdigit() or _is_range(p))]
    return ",".join(tokens) or None


def expand_selection(raw: str, count: int) -> list[int]:
    """Expand ``raw`` into concrete 1-based indices, clamped to ``[1, count]``.

    Ranges ``a-b`` expand inclusively (ascending or descending); order is preserved;
    out-of-range and invalid tokens are dropped. Returns ``[]`` when nothing valid.
    """
    indices: list[int] = []
    for part in raw.replace(" ", "").split(","):
        if part.isdigit():
            indices.append(int(part))
        elif _is_range(part):
            lo, hi = (int(b) for b in part.split("-"))
            step = 1 if hi >= lo else -1
            indices.extend(range(lo, hi + step, step))
    return [i for i in indices if 1 <= i <= count]


def _is_range(token: str) -> bool:
    """True for an ``"a-b"`` integer range token."""
    bits = token.split("-")
    return len(bits) == 2 and all(b.isdigit() for b in bits)
