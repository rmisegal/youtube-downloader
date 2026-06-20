"""Unit tests for the CLI --mix routing + exit-code mapping (SDK patched)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ytdl.cli import main as cli
from ytdl.cli import run as cli_run
from ytdl.shared.errors import PlaybackDependencyError, RateLimitExceededError


def _run(argv, sdk):
    with patch.object(cli_run, "YoutubeDownloaderSDK", return_value=sdk):
        return cli.main(argv)


def test_mix_delegates_with_parsed_args() -> None:
    sdk = MagicMock()
    sdk.mix_local_directory.return_value = {"mode": "option1", "track_count": 2}
    code = _run(
        ["--mix", "--dir", "C:/v", "--mode", "option1", "--selection", "manual",
         "--crossfade-time", "2", "--source-mix-time", "30", "--target-start-time", "10"],
        sdk,
    )
    assert code == cli.EXIT_SUCCESS
    sdk.mix_local_directory.assert_called_once_with(
        "C:/v",
        mode="option1",
        selection="manual",
        crossfade=2,
        source_mix_time=30.0,
        target_start_time=10.0,
    )


def test_mix_requires_dir() -> None:
    # No SDK construction needed: the --dir check short-circuits first.
    assert cli.main(["--mix"]) == cli.EXIT_USAGE


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (PlaybackDependencyError("no vlc"), cli.EXIT_PLAYBACK_DEP),
        (FileNotFoundError("missing dir"), cli.EXIT_USAGE),
        (RateLimitExceededError("429"), cli.EXIT_RATE_LIMIT),
        (RuntimeError("boom"), cli.EXIT_GENERIC_ERROR),
    ],
)
def test_mix_exception_maps_to_exit_code(exc, code, capsys) -> None:
    sdk = MagicMock()
    sdk.mix_local_directory.side_effect = exc
    assert _run(["--mix", "--dir", "C:/v"], sdk) == code
    assert "Error:" in capsys.readouterr().err


def test_mix_default_mode_passes_none_through() -> None:
    sdk = MagicMock()
    sdk.mix_local_directory.return_value = {"mode": "option2", "track_count": 1}
    _run(["--mix", "--dir", "C:/v"], sdk)
    kwargs = sdk.mix_local_directory.call_args.kwargs
    assert kwargs == {
        "mode": None,
        "selection": None,
        "crossfade": None,
        "source_mix_time": None,
        "target_start_time": None,
    }
