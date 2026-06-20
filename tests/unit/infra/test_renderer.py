"""Unit tests for :class:`MixRenderer` (PRD-playlist §6) — no real ffmpeg."""

from __future__ import annotations

from typing import Any

from ytdl.infra.playback.renderer import MixRenderer
from ytdl.services.mixer.segment import MixSegment


class _Ffmpeg:
    def exe(self) -> str:
        return "/fake/ffmpeg"


class _Config:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        node: Any = self._data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node


def _renderer(config: Any = None, **kw: Any) -> MixRenderer:
    return MixRenderer(ffmpeg=_Ffmpeg(), config=config, **kw)


def _segs(n: int = 3) -> list[MixSegment]:
    return [MixSegment(path=f"clip{i}.mp4", start=float(i), play_seconds=10.0) for i in range(n)]


def _pairs(cmd: list[str], flag: str) -> list[str]:
    """Return the argument following each ``flag`` occurrence in ``cmd``."""
    return [cmd[i + 1] for i, tok in enumerate(cmd) if tok == flag]


def test_each_segment_has_ss_and_t_before_input() -> None:
    cmd = _renderer().build_command(_segs(3), "out.mp4", crossfade=2)
    # Three -i inputs, each immediately preceded by -ss <start> -t <play>.
    inputs = [i for i, tok in enumerate(cmd) if tok == "-i"]
    assert len(inputs) == 3
    for i in inputs:
        assert cmd[i - 4] == "-ss"
        assert cmd[i - 2] == "-t"
        assert cmd[i - 1] == "10"
    assert _pairs(cmd, "-i") == ["clip0.mp4", "clip1.mp4", "clip2.mp4"]
    assert _pairs(cmd, "-ss") == ["0", "1", "2"]


def test_cumulative_xfade_offsets_for_three_segments() -> None:
    cmd = _renderer().build_command(_segs(3), "out.mp4", crossfade=2)
    graph = cmd[cmd.index("-filter_complex") + 1]
    # offset_1 = 10 - 1*2 = 8 ; offset_2 = 20 - 2*2 = 16
    assert "offset=8" in graph
    assert "offset=16" in graph
    assert graph.count("xfade=") == 2
    assert graph.count("acrossfade=") == 2


def test_speed_adds_setpts_and_atempo() -> None:
    segs = [MixSegment(path="a.mp4", play_seconds=5.0, speed=2.0), MixSegment(path="b.mp4", play_seconds=5.0)]
    graph = _renderer().build_command(segs, "out.mp4", crossfade=1)[
        _renderer().build_command(segs, "out.mp4", crossfade=1).index("-filter_complex") + 1
    ]
    assert "setpts=PTS/2" in graph
    assert "atempo=2" in graph


def test_resolution_adds_scale() -> None:
    segs = [MixSegment(path="a.mp4", play_seconds=5.0, resolution="1280x720"), MixSegment(path="b.mp4", play_seconds=5.0)]
    cmd = _renderer().build_command(segs, "out.mp4", crossfade=1)
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "scale=1280:720" in graph
    # the second segment ("max") gets no scale filter
    assert graph.count("scale=") == 1


def test_codecs_and_container_from_config() -> None:
    cfg = _Config({"render": {"video_codec": "libx264", "audio_codec": "aac", "container": "mp4"}})
    cmd = _renderer(cfg).build_command(_segs(2), "out.mp4", crossfade=1)
    assert _pairs(cmd, "-c:v") == ["libx264"]
    assert _pairs(cmd, "-c:a") == ["aac"]


def test_defaults_when_no_config() -> None:
    cmd = _renderer().build_command(_segs(2), "out.mp4", crossfade=1)
    assert "libx264" in cmd
    assert "aac" in cmd


def test_play_seconds_none_probes_duration() -> None:
    calls: list[str] = []

    def dur(path: str, _exe: str) -> float:
        calls.append(path)
        return 7.0

    segs = [MixSegment(path="a.mp4"), MixSegment(path="b.mp4", play_seconds=4.0)]
    cmd = _renderer(duration_fn=dur).build_command(segs, "out.mp4", crossfade=1)
    assert calls == ["a.mp4"]  # only the None one was probed
    assert _pairs(cmd, "-t") == ["7", "4"]


def test_leading_video_drops_leading_audio_members_supply_audio() -> None:
    cmd = _renderer().build_leading_command(_segs(2), "lead.mp4", "video", "out.mp4", crossfade=1)
    assert "-an" in cmd
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "acrossfade=" in graph  # members supply the audio mix
    # leading picture is mapped directly, not via a filter label
    assert "0:v" in cmd


def test_leading_audio_discards_picture_keeps_audio() -> None:
    cmd = _renderer().build_leading_command(_segs(2), "song.mp3", "audio", "out.mp4", crossfade=1)
    assert "-vn" in cmd
    assert "0:a" in cmd
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "xfade=" in graph  # members supply the video mix


def test_leading_member_inputs_shifted_by_one() -> None:
    cmd = _renderer().build_leading_command(_segs(2), "lead.mp4", "video", "out.mp4", crossfade=1)
    graph = cmd[cmd.index("-filter_complex") + 1]
    # leading is input 0, so members start at [1:a]/[2:a]
    assert "[1:a]" in graph
    assert "[0:a]" not in graph


def test_subtitle_file_adds_burn_filter() -> None:
    segs = [MixSegment(path="a.mp4", play_seconds=5.0, subtitle="subs.srt"), MixSegment(path="b.mp4", play_seconds=5.0)]
    graph = _renderer().build_command(segs, "out.mp4", crossfade=1)
    g = graph[graph.index("-filter_complex") + 1]
    assert "subtitles=subs.srt" in g


def test_subtitle_true_uses_embedded() -> None:
    segs = [MixSegment(path="a.mp4", play_seconds=5.0, subtitle=True), MixSegment(path="b.mp4", play_seconds=5.0)]
    cmd = _renderer().build_command(segs, "out.mp4", crossfade=1)
    g = cmd[cmd.index("-filter_complex") + 1]
    assert "subtitles=si=0" in g


def test_subtitle_none_adds_no_subtitle_filter() -> None:
    cmd = _renderer().build_command(_segs(2), "out.mp4", crossfade=1)
    g = cmd[cmd.index("-filter_complex") + 1]
    assert "subtitles=" not in g


def test_render_invokes_runner_with_argv() -> None:
    captured: list[list[str]] = []

    def runner(cmd: list[str], *_a: Any, **_k: Any) -> None:
        captured.append(cmd)

    out = _renderer(runner=runner).render(_segs(3), "C:/out", crossfade=2, name="show")
    assert len(captured) == 1
    assert captured[0][0] == "/fake/ffmpeg"
    assert "-y" in captured[0]
    assert out.replace("\\", "/").endswith("C:/out/show.mp4")
    assert captured[0][-1] == out


def test_render_uses_leading_command_when_kind_set() -> None:
    captured: list[list[str]] = []
    _renderer(runner=lambda c, *a, **k: captured.append(c)).render(
        _segs(2), "C:/out", crossfade=1, leading_path="lead.mp4", leading_kind="audio"
    )
    assert "-vn" in captured[0]
