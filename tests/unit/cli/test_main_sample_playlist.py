"""Unit tests for the CLI --sample-play / --playlist-file routing (SDK patched).

No network / no VLC: the SDK is fully mocked; we assert delegation + exit-code
mapping only (PRD-playlist §3.1, §5.1, §9).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ytdl.cli import main as cli
from ytdl.cli import run as cli_run
from ytdl.shared.errors import PlaybackDependencyError, PlaylistError


def _run(argv, sdk):
    with patch.object(cli_run, "YoutubeDownloaderSDK", return_value=sdk):
        return cli.main(argv)


def test_sample_play_delegates_with_parsed_args() -> None:
    sdk = MagicMock()
    sdk.sample_play.return_value = {"mode": "option1", "track_count": 3, "loop": True}
    code = _run(
        ["--sample-play", "--dir", "X", "--mode", "option1", "--play-for-sec", "5"],
        sdk,
    )
    assert code == cli.EXIT_SUCCESS
    sdk.sample_play.assert_called_once_with("X", play_for_sec=5.0, mode="option1")


def test_sample_play_default_mode_and_duration() -> None:
    sdk = MagicMock()
    sdk.sample_play.return_value = {"mode": "option2", "track_count": 1, "loop": True}
    assert _run(["--sample-play", "--dir", "X"], sdk) == cli.EXIT_SUCCESS
    sdk.sample_play.assert_called_once_with("X", play_for_sec=None, mode=None)


def test_sample_play_requires_dir() -> None:
    assert cli.main(["--sample-play"]) == cli.EXIT_USAGE


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (PlaybackDependencyError("no vlc"), cli.EXIT_PLAYBACK_DEP),
        (FileNotFoundError("bad dir"), cli.EXIT_USAGE),
        (RuntimeError("boom"), cli.EXIT_GENERIC_ERROR),
    ],
)
def test_sample_play_exception_maps_to_exit_code(exc, code, capsys) -> None:
    sdk = MagicMock()
    sdk.sample_play.side_effect = exc
    assert _run(["--sample-play", "--dir", "X"], sdk) == code
    assert "Error:" in capsys.readouterr().err


def test_playlist_file_delegates() -> None:
    sdk = MagicMock()
    sdk.play_playlist.return_value = {"output": {}, "summary": {}}
    assert _run(["--playlist-file", "p.yaml"], sdk) == cli.EXIT_SUCCESS
    sdk.play_playlist.assert_called_once_with("p.yaml")


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (PlaylistError("bad yaml"), cli.EXIT_PLAYLIST),
        (PlaybackDependencyError("no vlc"), cli.EXIT_PLAYBACK_DEP),
        (FileNotFoundError("missing"), cli.EXIT_USAGE),
        (RuntimeError("boom"), cli.EXIT_GENERIC_ERROR),
    ],
)
def test_playlist_exception_maps_to_exit_code(exc, code, capsys) -> None:
    sdk = MagicMock()
    sdk.play_playlist.side_effect = exc
    assert _run(["--playlist-file", "p.yaml"], sdk) == code
    assert "Error:" in capsys.readouterr().err
