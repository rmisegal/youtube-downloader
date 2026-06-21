"""Pick the right FFmpeg render command for a prepared clip list.

Routing for the visual base render: an absolute/music-sync timeline becomes a
crossfade (soft dissolves) or concat (clean cuts) for contiguous slots, the N-input
overlay compositor for an overlapping manual timeline, the leading-track command for
a leading video/audio master, or the plain sequential xfade otherwise. Kept out of
:mod:`sample_stream` so each file stays ≤150 lines.
"""

from __future__ import annotations

from ytdl.constants import LEADING_AUDIO, LEADING_VIDEO
from ytdl.infra.playback.concat import build_concat_command, is_contiguous
from ytdl.infra.playback.renderer import MixRenderer
from ytdl.infra.playback.timeline import build_timeline_command, timeline_total
from ytdl.infra.playback.xfade import build_xfade_command
from ytdl.services.mixer.segment import MixSegment


def render_command(
    renderer: MixRenderer,
    prepared: list[MixSegment],
    out_file: str,
    *,
    crossfade: float,
    leading_path: str | None,
    leading_kind: str,
    timeline: bool,
    tmp_dir: str,
    dissolve: float = 0.0,
) -> list[str]:
    """Pick the render command: crossfade/concat (contiguous), overlay, leading, or xfade."""
    if timeline:
        total = timeline_total(prepared)
        lead = leading_path
        if leading_path and leading_kind == LEADING_AUDIO:
            lead = renderer.looped_leading(leading_path, total, crossfade, tmp_dir)
        if is_contiguous(prepared):
            # Crossfade mode -> soft cross-dissolves (slower re-encode, no black);
            # otherwise fast concat (video stream-copied, clean cuts).
            if dissolve > 0 and len(prepared) > 1:
                return build_xfade_command(
                    renderer, prepared, total=total, leading_path=lead,
                    leading_kind=leading_kind, dissolve=dissolve, crossfade=crossfade,
                    output_path=out_file,
                )
            return build_concat_command(
                renderer, prepared, total=total, leading_path=lead,
                leading_kind=leading_kind, crossfade=crossfade,
                output_path=out_file, tmp_dir=tmp_dir,
            )
        # An OVERLAPPING manual timeline needs the N-input overlay compositor.
        return build_timeline_command(
            renderer, prepared, total=total, leading_path=lead,
            leading_kind=leading_kind, crossfade=crossfade, output_path=out_file,
        )
    if leading_path and leading_kind in (LEADING_VIDEO, LEADING_AUDIO):
        lead = leading_path
        if leading_kind == LEADING_AUDIO:
            video_seconds = sum(s.play_seconds or 0.0 for s in prepared) - crossfade * (
                len(prepared) - 1
            )
            lead = renderer.looped_leading(
                leading_path, max(0.0, video_seconds), crossfade, tmp_dir
            )
        return renderer.build_leading_command(
            prepared, lead, leading_kind, out_file, crossfade=crossfade
        )
    return renderer.build_command(prepared, out_file, crossfade=crossfade)
