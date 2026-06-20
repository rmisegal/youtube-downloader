"""Unit tests for CLI playlist resolution + rate-limit exit code.

``YoutubeDownloaderSDK`` is patched so nothing touches the network;
``resolve_playlist_choice`` is patched where it matters to avoid prompting.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ytdl.cli import main as cli
from ytdl.shared.errors import RateLimitExceededError

URL = "https://youtu.be/dQw4w9WgXcQ"
LIST_URL = "https://www.youtube.com/watch?v=X&list=Y"


def _run(argv, sdk):
    with patch.object(cli, "YoutubeDownloaderSDK", return_value=sdk) as klass:
        klass.version = MagicMock(return_value="1.00")
        return cli.main(argv)


def _args(**over) -> SimpleNamespace:
    base = {"url": URL, "no_playlist": False, "playlist_items": None}
    base.update(over)
    return SimpleNamespace(**base)


def test_rate_limit_exception_maps_to_exit_6(capsys) -> None:
    sdk = MagicMock()
    sdk.download.side_effect = RateLimitExceededError("quota")
    assert _run([URL], sdk) == cli.EXIT_RATE_LIMIT
    assert "Error:" in capsys.readouterr().err


def test_resolve_no_playlist_flag_skips_probe() -> None:
    sdk = MagicMock()
    choice = cli._resolve_playlist(sdk, _args(no_playlist=True))
    assert choice == {"no_playlist": True, "playlist_items": None}
    sdk.probe_playlist.assert_not_called()


def test_resolve_playlist_items_flag_skips_probe() -> None:
    sdk = MagicMock()
    choice = cli._resolve_playlist(sdk, _args(playlist_items="1,3"))
    assert choice == {"no_playlist": False, "playlist_items": "1,3"}
    sdk.probe_playlist.assert_not_called()


def test_resolve_playlist_url_calls_resolve_choice() -> None:
    sdk = MagicMock()
    sentinel = {"no_playlist": True, "playlist_items": None}
    with patch.object(cli, "resolve_playlist_choice", return_value=sentinel) as rpc:
        choice = cli._resolve_playlist(sdk, _args(url=LIST_URL))
    assert choice is sentinel
    rpc.assert_called_once_with(sdk, LIST_URL)


def test_resolve_plain_url_returns_default() -> None:
    sdk = MagicMock()
    choice = cli._resolve_playlist(sdk, _args(url=URL))
    assert choice == {"no_playlist": False, "playlist_items": None}
    sdk.probe_playlist.assert_not_called()
