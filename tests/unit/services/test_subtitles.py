"""Unit tests for :class:`ytdl.services.subtitles.SubtitleDownloader`.

``FfmpegLocator.exe_dir`` is patched to a fake dir; the config is driven via an
in-memory :class:`ConfigManager` — no real FFmpeg, no network.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

from ytdl.services.subtitles import SubtitleDownloader
from ytdl.shared.config import ConfigManager

FAKE_DIR = os.path.join(os.sep, "fake", "bin")
OUT_DIR = os.path.join(os.sep, "out")


def _make(defaults: dict[str, Any] | None = None) -> SubtitleDownloader:
    """A SubtitleDownloader backed by an in-memory config."""
    data: dict[str, Any] = {"version": "1.00"}
    if defaults is not None:
        data["defaults"] = defaults
    return SubtitleDownloader(ConfigManager(data=data))


def _build(
    dl: SubtitleDownloader,
    name: str | None = "sample",
    **kwargs: Any,
) -> dict[str, Any]:
    with patch("ytdl.infra.ffmpeg.FfmpegLocator.exe_dir", return_value=FAKE_DIR):
        return dl.build_opts(OUT_DIR, name, **kwargs)


def _convert_pp(opts: dict[str, Any]) -> dict[str, Any]:
    pps = opts["postprocessors"]
    return next(pp for pp in pps if pp["key"] == "FFmpegSubtitlesConvertor")


def test_manual_and_auto_subs_both_enabled() -> None:
    """opts request manual *and* auto-generated subtitles (PRD §3.2)."""
    opts = _build(_make({"sub_lang": "en"}))
    assert opts["writesubtitles"] is True
    assert opts["writeautomaticsub"] is True


def test_subtitleslangs_uses_explicit_kwarg() -> None:
    """An explicit ``sub_lang`` kwarg drives ``subtitleslangs``."""
    opts = _build(_make({"sub_lang": "en"}), sub_lang="es")
    assert opts["subtitleslangs"] == ["es"]


def test_default_lang_from_config_when_no_kwarg() -> None:
    """Without a kwarg, the language comes from ``defaults.sub_lang``."""
    opts = _build(_make({"sub_lang": "en"}))
    assert opts["subtitleslangs"] == ["en"]


def test_default_lang_when_defaults_section_absent() -> None:
    """Missing ``defaults`` config falls back to ``"en"`` (not crash)."""
    opts = _build(_make(defaults=None))
    assert opts["subtitleslangs"] == ["en"]


def test_config_lang_overrides_default_fallback() -> None:
    """A configured non-en language is used when no kwarg is given."""
    opts = _build(_make({"sub_lang": "fr"}))
    assert opts["subtitleslangs"] == ["fr"]


def test_subtitlesformat_is_srt() -> None:
    """The requested subtitle format is srt."""
    opts = _build(_make({"sub_lang": "en"}))
    assert opts["subtitlesformat"] == "srt"


def test_convertor_postprocessor_present_with_srt_format() -> None:
    """An FFmpegSubtitlesConvertor → srt post-processor guarantees srt output."""
    pp = _convert_pp(_build(_make({"sub_lang": "en"})))
    assert pp["key"] == "FFmpegSubtitlesConvertor"
    assert pp["format"] == "srt"


def test_auto_captions_fallback_still_converted_to_srt() -> None:
    """Auto-only case: writeautomaticsub True + convertor → srt is still set."""
    opts = _build(_make({"sub_lang": "en"}))
    assert opts["writeautomaticsub"] is True
    assert _convert_pp(opts)["format"] == "srt"


def test_exactly_one_convertor_postprocessor() -> None:
    """Edge: exactly one post-processor, the subtitle convertor."""
    opts = _build(_make({"sub_lang": "en"}))
    assert len(opts["postprocessors"]) == 1


def test_merged_opts_include_base_keys() -> None:
    """Merged opts still carry the base ``outtmpl`` and ``ffmpeg_location``."""
    opts = _build(_make({"sub_lang": "en"}), name="sample")
    assert opts["outtmpl"] == str(Path(OUT_DIR) / "sample.%(ext)s")
    assert opts["ffmpeg_location"] == FAKE_DIR


def test_mode_opts_only_adds_subtitle_keys() -> None:
    """The hook contributes only subtitle-related keys (overrides only)."""
    dl = _make({"sub_lang": "en"})
    assert set(dl._mode_opts()) == {
        "writesubtitles",
        "writeautomaticsub",
        "subtitleslangs",
        "subtitlesformat",
        "postprocessors",
    }
