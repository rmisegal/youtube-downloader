"""Unit tests for :mod:`ytdl.shared.selection`."""

from __future__ import annotations

import pytest

from ytdl.shared.selection import expand_selection, parse_selection


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


@pytest.mark.parametrize(
    ("raw", "count", "expected"),
    [
        ("1,3,5", 10, [1, 3, 5]),
        ("2-4", 10, [2, 3, 4]),
        ("1, 2-4 ,7", 10, [1, 2, 3, 4, 7]),
        ("3-1", 10, [3, 2, 1]),          # descending range
        ("1,99,3", 5, [1, 3]),           # out-of-range dropped
        ("0,2", 5, [2]),                 # below 1 dropped
        ("x,,-", 5, []),                 # all invalid
        ("", 5, []),
    ],
)
def test_expand_selection(raw: str, count: int, expected: list[int]) -> None:
    assert expand_selection(raw, count) == expected
