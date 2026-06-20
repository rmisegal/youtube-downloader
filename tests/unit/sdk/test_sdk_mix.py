"""Unit tests for the SDK mixer entry point + build_mixer wiring (no VLC/network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ytdl.sdk import sdk as sdk_module
from ytdl.sdk.sdk import YoutubeDownloaderSDK
from ytdl.sdk.wiring import build_mixer
from ytdl.services.mixer.mixer_service import MixerService
from ytdl.shared.config import ConfigManager


def _sdk() -> YoutubeDownloaderSDK:
    return YoutubeDownloaderSDK(
        client=MagicMock(),
        config=ConfigManager(data={"version": "1.02"}),
        rate_config=ConfigManager(data={"version": "1.02"}),
    )


def test_mix_local_directory_delegates_to_mixer() -> None:
    mixer = MagicMock()
    mixer.mix.return_value = {"mode": "option1", "track_count": 3}
    sdk = _sdk()
    with patch.object(sdk_module, "build_mixer", return_value=mixer) as build:
        out = sdk.mix_local_directory(
            "C:/videos",
            mode="option1",
            selection="manual",
            crossfade=2,
            source_mix_time=30.0,
            target_start_time=10.0,
        )
    assert out == {"mode": "option1", "track_count": 3}
    # SDK passes itself as the rate-limited downloader for YouTube injection.
    assert build.call_args.kwargs["downloader"] is sdk
    mixer.mix.assert_called_once_with(
        "C:/videos",
        mode="option1",
        selection="manual",
        crossfade=2,
        source_mix_time=30.0,
        target_start_time=10.0,
    )


def test_build_mixer_returns_mixer_service() -> None:
    mixer = build_mixer(ConfigManager(data={"version": "1.02"}), downloader=object())
    assert isinstance(mixer, MixerService)
