"""Leading-track command assembly for :class:`MixRenderer` (PRD-playlist §6).

Split out of :mod:`ytdl.infra.playback.renderer` to keep each file ≤150 lines.
``leading=video`` keeps the leading picture and drops its audio (``-an``), members
supply the audio mix; ``leading=audio`` keeps only the leading audio (``-vn``),
members supply the video mix. Member graph indices are bumped (leading is input 0).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ytdl.infra.playback.renderer_graph import (
    build_audio_graph,
    build_video_graph,
    bump_indices,
)
from ytdl.services.mixer.segment import MixSegment


def leading_command(
    renderer: Any,
    segments: Sequence[MixSegment],
    leading_path: str,
    leading_kind: str,
    output_path: str,
    *,
    crossfade: float,
) -> list[str]:
    """Build the render argv with a leading video (``-an``) or audio (``-vn``) master."""
    durations = renderer._durations(segments)
    if leading_kind == "video":
        asteps, alabel = _shifted(renderer, build_audio_graph, segments, durations, crossfade)
        graph = ";".join(asteps)  # leading picture kept as-is; only audio mixed
        lead_in = ["-an", "-i", leading_path]
        return _assemble(renderer, lead_in, segments, durations, graph, "0:v", f"[{alabel}]", output_path)
    # leading_kind == "audio": members' picture is xfaded; the leading track is the
    # soundtrack. The audio is LOOPED to cover the video and TRIMMED to the exact
    # video length with a fade-out (dim) at the end — so it never plays over a black
    # tail (song longer than video) and a short song still fills the mix (PRD-playlist §6).
    vsteps, vlabel = _shifted(renderer, build_video_graph, segments, durations, crossfade)
    total = _video_total(durations, crossfade)
    fade_start = max(0.0, total - crossfade)
    aud = (
        f"[0:a]atrim=0:{_fmt(total)},"
        f"afade=t=out:st={_fmt(fade_start)}:d={_fmt(crossfade)}[aout]"
    )
    graph = ";".join([*vsteps, aud])
    lead_in = ["-stream_loop", "-1", "-vn", "-i", leading_path]
    return _assemble(
        renderer, lead_in, segments, durations, graph, f"[{vlabel}]", "[aout]", output_path
    )


def _fmt(value: float) -> str:
    """Format a time compactly (no trailing ``.0``)."""
    return str(int(value)) if float(value).is_integer() else f"{value:.3f}"


def _video_total(durations: Sequence[float], crossfade: float) -> float:
    """Total xfade-mix duration: clips overlap by ``crossfade`` at each join."""
    if not durations:
        return 0.0
    return max(0.0, sum(durations) - crossfade * (len(durations) - 1))


def _shifted(renderer, builder, segments, durations, crossfade):  # type: ignore[no-untyped-def]
    """Build a member graph whose input indices start at 1 (leading is input 0)."""
    if builder is build_video_graph:
        steps, label = builder(segments, durations, crossfade, renderer._canvas, renderer._fps)
    else:
        steps, label = builder(segments, durations, crossfade)
    return [bump_indices(s, len(segments)) for s in steps], label


def _assemble(renderer, lead_in, segments, durations, graph, vmap, amap, output_path):  # type: ignore[no-untyped-def]
    """Combine leading input, members, graph and pre-formatted maps into argv."""
    return [
        renderer._ffmpeg.exe(),
        "-y",
        *lead_in,
        *renderer._inputs(segments, durations),
        "-filter_complex",
        graph,
        "-map",
        vmap,
        "-map",
        amap,
        *renderer._codec_out(output_path),
    ]
