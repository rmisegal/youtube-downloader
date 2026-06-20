"""Unit tests for :class:`PlaylistError` (PRD-playlist §9, exit code 8)."""

from __future__ import annotations

from ytdl.shared.errors import PlaylistError, YtdlError


def test_playlist_error_subclasses_ytdl_error() -> None:
    assert issubclass(PlaylistError, YtdlError)


def test_playlist_error_is_raisable() -> None:
    err = PlaylistError("bad playlist")
    assert isinstance(err, YtdlError)
    assert str(err) == "bad playlist"
