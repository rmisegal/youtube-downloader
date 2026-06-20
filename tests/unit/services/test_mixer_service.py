"""Unit tests for :class:`ytdl.services.mixer.mixer_service.MixerService`.

All collaborators are :class:`MagicMock`; no network, VLC, or FFmpeg is touched.
Config defaults come from an in-memory :class:`ConfigManager` mirroring the
``playback`` block of ``config/setup.json``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ytdl.constants import PLAYBACK_OPTION1, PLAYBACK_OPTION2, SELECTION_RANDOM
from ytdl.services.mixer.mixer_service import MixerService
from ytdl.shared.config import ConfigManager
from ytdl.shared.errors import PlaybackDependencyError

_PLAYBACK = {
    "default_mode": PLAYBACK_OPTION2,
    "default_selection": SELECTION_RANDOM,
    "crossfade_duration_seconds": 3,
    "source_mix_time_seconds": None,
    "target_start_time_seconds": 0,
}
_TRACKS = [Path("a.mp4"), Path("b.mp4")]


def _config() -> ConfigManager:
    return ConfigManager(data={"version": "1.02", "playback": dict(_PLAYBACK)})


def _service(downloader: MagicMock | None = None) -> dict[str, MagicMock | MixerService]:
    playlist = MagicMock()
    playlist.scan.return_value = ["raw"]
    playlist.select.return_value = list(_TRACKS)
    vlc_locator = MagicMock()
    vlc_locator.vlc_binary.return_value = "/usr/bin/vlc"
    stream_server = MagicMock()
    matrix = MagicMock()
    service = MixerService(
        _config(), playlist, vlc_locator, stream_server, matrix, downloader=downloader
    )
    return {
        "service": service,
        "playlist": playlist,
        "vlc_locator": vlc_locator,
        "stream_server": stream_server,
        "matrix": matrix,
    }


def test_option2_is_default_and_runs_matrix() -> None:
    """No mode given → ensure_libvlc + matrix.play_sequence; stream untouched."""
    d = _service()
    result = d["service"].mix("media")
    d["vlc_locator"].ensure_libvlc.assert_called_once()
    d["vlc_locator"].vlc_binary.assert_not_called()
    d["matrix"].play_sequence.assert_called_once_with(
        _TRACKS, crossfade=3, source_mix_time=None, target_start_time=0
    )
    d["stream_server"].run.assert_not_called()
    assert result == {
        "mode": PLAYBACK_OPTION2,
        "selection": SELECTION_RANDOM,
        "track_count": 2,
        "crossfade": 3,
        "source_mix_time": None,
        "target_start_time": 0,
    }


def test_option1_locates_binary_and_runs_stream() -> None:
    """Option 1 → vlc_binary + stream_server.run with the binary; matrix idle."""
    d = _service()
    d["service"].mix("media", mode=PLAYBACK_OPTION1)
    d["vlc_locator"].vlc_binary.assert_called_once()
    d["vlc_locator"].ensure_libvlc.assert_not_called()
    d["stream_server"].run.assert_called_once_with(
        _TRACKS,
        crossfade=3,
        source_mix_time=None,
        target_start_time=0,
        vlc_binary="/usr/bin/vlc",
    )
    d["matrix"].play_sequence.assert_not_called()


def test_select_wires_scan_output() -> None:
    """select(scan(dir), selection) is the queue-building contract."""
    d = _service()
    d["service"].mix("media", selection="manual")
    d["playlist"].scan.assert_called_once_with("media")
    d["playlist"].select.assert_called_once_with(["raw"], "manual")


def test_explicit_timing_overrides_config_for_matrix() -> None:
    """Explicit crossfade/timing reach the Option-2 engine verbatim."""
    d = _service()
    d["service"].mix(
        "media", crossfade=7, source_mix_time=12.5, target_start_time=4.0
    )
    d["matrix"].play_sequence.assert_called_once_with(
        _TRACKS, crossfade=7, source_mix_time=12.5, target_start_time=4.0
    )


def test_explicit_timing_overrides_config_for_stream() -> None:
    """Explicit timing reaches the Option-1 engine verbatim."""
    d = _service()
    d["service"].mix(
        "media",
        mode=PLAYBACK_OPTION1,
        crossfade=5,
        source_mix_time=9.0,
        target_start_time=2.0,
    )
    d["stream_server"].run.assert_called_once_with(
        _TRACKS,
        crossfade=5,
        source_mix_time=9.0,
        target_start_time=2.0,
        vlc_binary="/usr/bin/vlc",
    )


def test_missing_vlc_propagates() -> None:
    """A locator raising PlaybackDependencyError bubbles out of mix()."""
    d = _service()
    d["vlc_locator"].vlc_binary.side_effect = PlaybackDependencyError("install VLC")
    with pytest.raises(PlaybackDependencyError):
        d["service"].mix("media", mode=PLAYBACK_OPTION1)


def test_unknown_mode_raises_value_error() -> None:
    """An unrecognized mode is rejected before any engine call."""
    d = _service()
    with pytest.raises(ValueError, match="bogus"):
        d["service"].mix("media", mode="bogus")
    d["stream_server"].run.assert_not_called()
    d["matrix"].play_sequence.assert_not_called()


def test_inject_youtube_uses_downloader() -> None:
    """inject_youtube delegates to the injected downloader and returns its result."""
    downloader = MagicMock()
    downloader.download.return_value = {"filepath": "cached.mp4"}
    d = _service(downloader=downloader)
    result = d["service"].inject_youtube("http://yt/x", "out")
    downloader.download.assert_called_once_with("http://yt/x", output_dir="out")
    assert result == {"filepath": "cached.mp4"}


def test_inject_youtube_without_downloader_raises() -> None:
    """No downloader configured → ValueError."""
    d = _service()
    with pytest.raises(ValueError, match="downloader"):
        d["service"].inject_youtube("http://yt/x", "out")


def test_inject_local_returns_path() -> None:
    """inject_local normalizes the input to a Path."""
    d = _service()
    assert d["service"].inject_local("clip.mp4") == Path("clip.mp4")
