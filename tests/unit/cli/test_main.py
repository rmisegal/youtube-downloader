"""Unit tests for :mod:`ytdl.cli.main` (no network; SDK is patched).

The CLI must contain NO business logic: these tests assert that argparse parses
every flag, that ``--version`` prints code+config version, that the SDK is
called with the parsed kwargs, and that each domain exception maps to its
deterministic exit code (PRD §3.3).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ytdl.cli import main as cli
from ytdl.shared.errors import (
    ConfigVersionError,
    InvalidUrlError,
    NetworkError,
    UnsupportedRequestError,
)

URL = "https://youtu.be/dQw4w9WgXcQ"


def _run(argv, sdk):
    """Run the CLI with ``YoutubeDownloaderSDK`` patched to ``sdk``."""
    with patch.object(cli, "YoutubeDownloaderSDK", return_value=sdk) as cls:
        cls.version = MagicMock(return_value="1.00")
        return cli.main(argv)


def test_all_flags_parse_and_delegate() -> None:
    """Every flag parses and is passed to ``SDK.download`` verbatim."""
    sdk = MagicMock()
    sdk.download.return_value = {"modes": ["video"], "output_dir": "out"}
    code = _run(
        [URL, "--video", "--audio", "--subs", "-o", "out", "-n", "sample",
         "--resolution", "720", "--sub-lang", "he"],
        sdk,
    )
    assert code == cli.EXIT_SUCCESS
    sdk.download.assert_called_once_with(
        URL,
        video=True,
        audio=True,
        subs=True,
        output_dir="out",
        name="sample",
        resolution=720,
        sub_lang="he",
        no_playlist=False,
        playlist_items=None,
    )


def test_resolution_parsed_as_int() -> None:
    """``--resolution`` is parsed as an int, not a string."""
    sdk = MagicMock()
    sdk.download.return_value = {"modes": ["video"], "output_dir": "."}
    _run([URL, "--resolution", "1080"], sdk)
    assert sdk.download.call_args.kwargs["resolution"] == 1080


def test_default_no_flags_passes_all_false() -> None:
    """No output flags → flags passed as given (SDK decides the video default)."""
    sdk = MagicMock()
    sdk.download.return_value = {"modes": ["video"], "output_dir": "."}
    code = _run([URL], sdk)
    assert code == cli.EXIT_SUCCESS
    kwargs = sdk.download.call_args.kwargs
    assert kwargs == {
        "video": False,
        "audio": False,
        "subs": False,
        "output_dir": None,
        "name": None,
        "resolution": None,
        "sub_lang": None,
        "no_playlist": False,
        "playlist_items": None,
    }


def test_version_prints_code_and_config(capsys) -> None:
    """``--version`` prints code + config version and returns 0."""
    fake_config = MagicMock()
    fake_config.version = "1.00"
    with patch.object(cli, "ConfigManager", return_value=fake_config), \
         patch.object(cli.logsetup, "configure_logging"), \
         patch.object(cli.YoutubeDownloaderSDK, "version", return_value="1.00"):
        code = cli.main(["--version"])
    out = capsys.readouterr().out
    assert code == cli.EXIT_SUCCESS
    assert "1.00" in out
    assert "code version" in out
    assert "config version" in out


def test_missing_url_is_usage_error() -> None:
    """No URL and no --version → usage error exit code."""
    assert cli.main([]) == cli.EXIT_USAGE


@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (InvalidUrlError("bad"), cli.EXIT_INVALID_URL),
        (NetworkError("net"), cli.EXIT_NETWORK_ERROR),
        (UnsupportedRequestError("nope"), cli.EXIT_UNSUPPORTED),
        (ConfigVersionError("ver"), cli.EXIT_CONFIG_VERSION),
        (RuntimeError("boom"), cli.EXIT_GENERIC_ERROR),
    ],
)
def test_exception_maps_to_exit_code(exc, code, capsys) -> None:
    """Each domain exception maps to its deterministic exit code (PRD §3.3)."""
    sdk = MagicMock()
    sdk.download.side_effect = exc
    assert _run([URL], sdk) == code
    assert "Error:" in capsys.readouterr().err


def test_success_returns_zero() -> None:
    """A clean download returns exit code 0."""
    sdk = MagicMock()
    sdk.download.return_value = {"modes": ["video"], "output_dir": "."}
    assert _run([URL], sdk) == cli.EXIT_SUCCESS


def test_command_lists_run_commands_with_examples(capsys) -> None:
    """``--command`` prints the run-command cheat-sheet and returns 0."""
    code = cli.main(["--command"])
    out = capsys.readouterr().out
    assert code == cli.EXIT_SUCCESS
    assert "uv run python -m ytdl" in out
    assert "--audio" in out
    assert "--subs" in out


def test_command_single_dash_alias_works(capsys) -> None:
    """``-command`` (single dash, as requested) is accepted as an alias."""
    code = cli.main(["-command"])
    assert code == cli.EXIT_SUCCESS
    assert "uv run python -m ytdl" in capsys.readouterr().out


def test_command_does_not_require_url() -> None:
    """``--command`` short-circuits before the URL-required check (no SDK call)."""
    sdk = MagicMock()
    code = _run(["--command"], sdk)
    assert code == cli.EXIT_SUCCESS
    sdk.download.assert_not_called()


def test_io_reconfigure_guarded() -> None:
    """_configure_io tolerates streams without reconfigure (no crash)."""
    cli._configure_io()  # smoke: must not raise in test environment
