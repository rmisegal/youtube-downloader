"""Interactive playlist resolution for the CLI.

When a URL belongs to a playlist/mix, ask the user whether to download the whole
list (showing the total number of AVAILABLE items), just this video, or a
selection of specific item numbers. Pure presentation + small parsing; all I/O is
injectable so it is fully testable and never required (flags or non-TTY skip it).
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

# A choice result the CLI passes straight to ``SDK.download``.
Choice = dict[str, Any]


def is_playlist_url(url: str) -> bool:
    """True if the URL references a playlist/mix (``list=`` query or ``/playlist``)."""
    lowered = url.lower()
    return "list=" in lowered or "/playlist" in lowered


def parse_selection(raw: str) -> str | None:
    """Normalize ``"1, 3 ,5 , 2-4"`` into yt-dlp ``playlist_items`` (``"1,3,5,2-4"``).

    Keeps integers and ``a-b`` ranges; drops empty/invalid tokens. Returns ``None``
    when nothing valid remains.
    """
    tokens = []
    for part in raw.replace(" ", "").split(","):
        if not part:
            continue
        if part.isdigit() or _is_range(part):
            tokens.append(part)
    return ",".join(tokens) or None


def _is_range(token: str) -> bool:
    """True for a ``"a-b"`` integer range token."""
    bits = token.split("-")
    return len(bits) == 2 and all(b.isdigit() for b in bits)


def resolve_playlist_choice(
    sdk: Any,
    url: str,
    *,
    input_fn: Callable[[str], str] = input,
    tty: bool | None = None,
) -> Choice:
    """Decide playlist handling for ``url`` (prompting only on a TTY).

    Returns ``{"no_playlist": bool, "playlist_items": str | None}``.
    """
    info = sdk.probe_playlist(url)
    if not info or info.get("count", 0) <= 1:
        return {"no_playlist": False, "playlist_items": None}
    interactive = sys.stdin.isatty() if tty is None else tty
    if not interactive:
        return _default_choice(url)
    try:
        return _prompt(info, input_fn)
    except EOFError:
        # stdin claims to be a TTY but no input is readable (piped/CI shells).
        # Fall back to the safe default rather than crashing.
        return _default_choice(url)


def _default_choice(url: str) -> Choice:
    """Safe non-interactive default: a ``watch?v=...&list=...`` URL means just
    this video; a bare playlist URL means the whole list."""
    lowered = url.lower()
    return {"no_playlist": "list=" in lowered and "v=" in lowered, "playlist_items": None}


def _prompt(info: dict[str, Any], input_fn: Callable[[str], str]) -> Choice:
    """Ask all / select / only-this-video and build the choice."""
    count = info["count"]
    print(f"This URL is a playlist: {info.get('title')!r} with {count} available items.")
    choice = input_fn(
        f"Download [a]ll {count}, [s]elect specific items, or [o]nly this video? [a/s/o]: "
    ).strip().lower()
    if choice == "o":
        return {"no_playlist": True, "playlist_items": None}
    if choice == "s":
        for entry in info["entries"]:
            print(f"  {entry['index']}. {entry['title']}")
        raw = input_fn("Enter item numbers comma-separated (e.g. 1,3,5): ")
        return {"no_playlist": False, "playlist_items": parse_selection(raw)}
    return {"no_playlist": False, "playlist_items": None}
