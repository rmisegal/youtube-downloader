"""SDK Phase-6 surface tests: ``sample_play`` + ``play_playlist`` (no VLC/network).

All boundaries are mocked: the wiring builders are patched to return MagicMock
runners, so these assert the thin SDK methods delegate correctly (Rule 1).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ytdl.sdk import sdk as sdk_module
from ytdl.sdk.sdk import YoutubeDownloaderSDK
from ytdl.shared.config import ConfigManager


def _sdk() -> YoutubeDownloaderSDK:
    return YoutubeDownloaderSDK(
        client=MagicMock(),
        config=ConfigManager(data={"version": "1.02"}),
        rate_config=ConfigManager(data={"version": "1.02"}),
    )


def test_sample_play_delegates_to_sample_runner() -> None:
    runner = MagicMock()
    runner.run.return_value = {"mode": "option2", "track_count": 4, "loop": True}
    sdk = _sdk()
    with patch.object(sdk_module, "build_sample_runner", return_value=runner) as build:
        out = sdk.sample_play("C:/videos", play_for_sec=5.0, mode="option1")
    assert out == {"mode": "option2", "track_count": 4, "loop": True}
    assert build.call_args.args[0] is sdk._config
    runner.run.assert_called_once_with("C:/videos", play_for_sec=5.0, mode="option1")


def test_play_playlist_delegates_to_playlist_runner() -> None:
    runner = MagicMock()
    runner.run.return_value = {"outputs": ["display"], "track_count": 2}
    sdk = _sdk()
    with patch.object(sdk_module, "build_playlist_runner", return_value=runner) as build:
        out = sdk.play_playlist("show.yaml")
    assert out == {"outputs": ["display"], "track_count": 2}
    # SDK passes itself as the rate-limited downloader for URL members.
    assert build.call_args.kwargs["downloader"] is sdk
    runner.run.assert_called_once_with("show.yaml")
