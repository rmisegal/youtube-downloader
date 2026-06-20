"""Filtergraph string builders for :class:`MixRenderer` (PRD-playlist §12).

Per-segment normalization (``scale``/``fps``/``setsar`` + ``setpts``/``atempo``
for speed + optional subtitle insert/burn) BEFORE the ``xfade``/``acrossfade``
chain, with cumulative offsets. Kept separate so each file stays ≤150 lines.
"""

from __future__ import annotations

from collections.abc import Sequence

from ytdl.services.mixer.segment import MixSegment

# Normalization defaults applied to every input before xfade (PRD §12).
_FPS = 30
_SAR = "1"


def _fmt(value: float) -> str:
    """Format a time/duration compactly (no trailing ``.0``)."""
    return str(int(value)) if float(value).is_integer() else str(value)


def _video_norm(seg: MixSegment, idx: int, label: str) -> str:
    """Normalization chain for one video input → labelled output ``label``."""
    steps: list[str] = []
    if seg.resolution and seg.resolution != "max":
        steps.append(f"scale={seg.resolution.replace('x', ':')}")
    steps.append(f"fps={_FPS}")
    steps.append(f"setsar={_SAR}")
    if seg.speed != 1.0:
        steps.append(f"setpts=PTS/{_fmt(seg.speed)}")
    if isinstance(seg.subtitle, str):
        steps.append(f"subtitles={seg.subtitle}")
    elif seg.subtitle is True:
        steps.append("subtitles=si=0")
    chain = ",".join(steps)
    return f"[{idx}:v]{chain}[{label}]"


def _audio_norm(seg: MixSegment, idx: int, label: str) -> str:
    """Normalization chain for one audio input → labelled output ``label``."""
    steps = ["aresample=async=1"]
    if seg.speed != 1.0:
        steps.append(f"atempo={_fmt(seg.speed)}")
    chain = ",".join(steps)
    return f"[{idx}:a]{chain}[{label}]"


def _play_seconds(seg: MixSegment, durations: Sequence[float], idx: int) -> float:
    """Resolved play window for ``seg`` (probed duration when ``None``)."""
    return seg.play_seconds if seg.play_seconds is not None else durations[idx]


def _offsets(segments: Sequence[MixSegment], durations: Sequence[float], crossfade: float) -> list[float]:
    """Cumulative xfade offsets: offset_k = sum(play[0..k]) − k·crossfade."""
    offsets: list[float] = []
    cumulative = 0.0
    for k in range(len(segments) - 1):
        cumulative += _play_seconds(segments[k], durations, k)
        offsets.append(cumulative - (k + 1) * crossfade)
    return offsets


def _chain(labels: Sequence[str], offsets: Sequence[float], effect: str, crossfade: float, kind: str) -> tuple[list[str], str]:
    """Fold normalized ``labels`` into a single xfade/acrossfade output label."""
    steps: list[str] = []
    current = labels[0]
    for i in range(1, len(labels)):
        out = "v" if i == len(labels) - 1 and kind == "v" else f"{kind}x{i}"
        if i == len(labels) - 1 and kind == "a":
            out = "a"
        if kind == "v":
            steps.append(
                f"[{current}][{labels[i]}]xfade=transition={effect}:"
                f"duration={_fmt(crossfade)}:offset={_fmt(offsets[i - 1])}[{out}]"
            )
        else:
            steps.append(f"[{current}][{labels[i]}]acrossfade=d={_fmt(crossfade)}[{out}]")
        current = out
    return steps, current


def build_video_graph(segments: Sequence[MixSegment], durations: Sequence[float], crossfade: float) -> tuple[list[str], str]:
    """Return (filter steps, final label) for the members' video xfade chain."""
    norms = [_video_norm(s, i, f"v{i}") for i, s in enumerate(segments)]
    offsets = _offsets(segments, durations, crossfade)
    chain, label = _chain([f"v{i}" for i in range(len(segments))], offsets, segments[0].effect, crossfade, "v")
    return norms + chain, label


def build_audio_graph(segments: Sequence[MixSegment], durations: Sequence[float], crossfade: float) -> tuple[list[str], str]:
    """Return (filter steps, final label) for the members' audio acrossfade chain."""
    norms = [_audio_norm(s, i, f"a{i}") for i, s in enumerate(segments)]
    offsets = _offsets(segments, durations, crossfade)
    chain, label = _chain([f"a{i}" for i in range(len(segments))], offsets, segments[0].effect, crossfade, "a")
    return norms + chain, label


def bump_indices(step: str, count: int) -> str:
    """Shift input-stream indices ``[i:v]``/``[i:a]`` up by one for a leading track."""
    out = step
    for i in reversed(range(count)):
        out = out.replace(f"[{i}:v]", f"[{i + 1}:v]").replace(f"[{i}:a]", f"[{i + 1}:a]")
    return out
