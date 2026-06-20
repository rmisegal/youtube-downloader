"""Unit tests for :mod:`ytdl.cli.playlist` (pure parsing + injected I/O).

No real stdin: ``tty`` and ``input_fn`` are passed explicitly. ``probe_playlist``
is mocked on a fake SDK so nothing touches the network.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ytdl.cli.playlist import (
    is_playlist_url,
    parse_selection,
    resolve_playlist_choice,
)

WATCH_LIST = "https://www.youtube.com/watch?v=X&list=Y"
BARE_LIST = "https://www.youtube.com/playlist?list=Y"
PLAIN_WATCH = "https://www.youtube.com/watch?v=X"
SHORT = "https://youtu.be/ID"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (WATCH_LIST, True),
        (BARE_LIST, True),
        (PLAIN_WATCH, False),
        (SHORT, False),
    ],
)
def test_is_playlist_url(url: str, expected: bool) -> None:
    assert is_playlist_url(url) is expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1, 3 ,5", "1,3,5"),
        ("2-4", "2-4"),
        ("1, 2-4 ,x,,7", "1,2-4,7"),
        ("x,,-,3-", None),
        ("", None),
    ],
)
def test_parse_selection(raw: str, expected: str | None) -> None:
    assert parse_selection(raw) == expected


def _sdk(info: dict[str, Any] | None) -> MagicMock:
    sdk = MagicMock(name="SDK")
    sdk.probe_playlist.return_value = info
    return sdk


def _info(count: int) -> dict[str, Any]:
    return {
        "title": "My List",
        "count": count,
        "entries": [{"index": i, "id": f"v{i}", "title": f"T{i}"} for i in range(1, count + 1)],
    }


def test_single_video_count_one() -> None:
    choice = resolve_playlist_choice(_sdk(_info(1)), WATCH_LIST, tty=True, input_fn=lambda _: "a")
    assert choice == {"no_playlist": False, "playlist_items": None}


def test_probe_returns_none() -> None:
    choice = resolve_playlist_choice(_sdk(None), WATCH_LIST, tty=True, input_fn=lambda _: "a")
    assert choice == {"no_playlist": False, "playlist_items": None}


def test_non_tty_watch_and_list_means_single() -> None:
    choice = resolve_playlist_choice(_sdk(_info(3)), WATCH_LIST, tty=False, input_fn=lambda _: "a")
    assert choice == {"no_playlist": True, "playlist_items": None}


def test_non_tty_bare_playlist_means_all() -> None:
    choice = resolve_playlist_choice(_sdk(_info(3)), BARE_LIST, tty=False, input_fn=lambda _: "a")
    assert choice == {"no_playlist": False, "playlist_items": None}


def test_tty_only_this_video() -> None:
    choice = resolve_playlist_choice(_sdk(_info(3)), WATCH_LIST, tty=True, input_fn=lambda _: "o")
    assert choice == {"no_playlist": True, "playlist_items": None}


def test_tty_select_specific_items_prints_entries(capsys) -> None:
    answers = iter(["s", "1,3"])
    choice = resolve_playlist_choice(
        _sdk(_info(3)), WATCH_LIST, tty=True, input_fn=lambda _: next(answers)
    )
    assert choice == {"no_playlist": False, "playlist_items": "1,3"}
    out = capsys.readouterr().out
    assert "1. T1" in out
    assert "3. T3" in out


@pytest.mark.parametrize("answer", ["a", "zzz"])
def test_tty_all_or_other_returns_all(answer: str) -> None:
    choice = resolve_playlist_choice(
        _sdk(_info(3)), WATCH_LIST, tty=True, input_fn=lambda _: answer
    )
    assert choice == {"no_playlist": False, "playlist_items": None}


def _raise_eof(_prompt: str) -> str:
    raise EOFError


def test_tty_eof_falls_back_to_default() -> None:
    """A TTY that yields no readable input (EOF) falls back to the safe default."""
    watch = resolve_playlist_choice(_sdk(_info(3)), WATCH_LIST, tty=True, input_fn=_raise_eof)
    assert watch == {"no_playlist": True, "playlist_items": None}
    bare = resolve_playlist_choice(_sdk(_info(3)), BARE_LIST, tty=True, input_fn=_raise_eof)
    assert bare == {"no_playlist": False, "playlist_items": None}
