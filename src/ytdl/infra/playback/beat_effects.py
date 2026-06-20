"""Beat-reactive image animations (PRD-beatsync §4) — pulse/shake/bounce/flash.

Each effect oscillates at the music tempo: ``f = bpm/60`` beats per second, driven
by the zoompan output-frame counter ``on`` (time = ``on/fps``). They make a still
image throb/shake/bob/flash IN TIME with the soundtrack, so the sync placer can fit
an energetic effect to high-energy sync points (chorus/drop/build-up).
"""

from __future__ import annotations

from ytdl.constants import (
    TRANSITION_BOUNCE,
    TRANSITION_FLASH,
    TRANSITION_PULSE,
    TRANSITION_SHAKE,
)
from ytdl.infra.playback.renderer_graph import _fmt

_DEFAULT_BPM = 120.0
_CENTRE_X = "iw/2-(iw/zoom/2)"
_CENTRE_Y = "ih/2-(ih/zoom/2)"


def _zoompan(z: str, x: str, y: str, frames: int, w: int, h: int, fps: int) -> str:
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={fps}"


def beat_animation(name: str, frames: int, w: int, h: int, fps: int, bpm: float) -> str:
    """Return the FFmpeg filter(s) for a beat-reactive effect, or ``""`` if unknown."""
    f = _fmt(max(0.1, (bpm or _DEFAULT_BPM) / 60.0))  # beats per second
    beat = f"PI*{f}*on/{fps}"  # phase: one half-sine thump per beat
    if name == TRANSITION_PULSE:
        return _zoompan(f"1.0+0.07*abs(sin({beat}))", _CENTRE_X, _CENTRE_Y, frames, w, h, fps)
    if name == TRANSITION_BOUNCE:
        y = f"ih/2-(ih/zoom/2)-(ih*0.03)*abs(sin({beat}))"
        return _zoompan("1.1", _CENTRE_X, y, frames, w, h, fps)
    if name == TRANSITION_SHAKE:
        fx, fy = _fmt(max(0.1, (bpm or _DEFAULT_BPM) / 60.0) * 4), _fmt(
            max(0.1, (bpm or _DEFAULT_BPM) / 60.0) * 5
        )
        x = f"iw/2-(iw/zoom/2)+(iw*0.012)*sin(2*PI*{fx}*on/{fps})"
        y = f"ih/2-(ih/zoom/2)+(ih*0.012)*cos(2*PI*{fy}*on/{fps})"
        return _zoompan("1.12", x, y, frames, w, h, fps)
    if name == TRANSITION_FLASH:
        zp = _zoompan(f"1.0+0.03*abs(sin({beat}))", _CENTRE_X, _CENTRE_Y, frames, w, h, fps)
        return f"{zp},eq=brightness='0.12*abs(sin(PI*{f}*t))':eval=frame"
    return ""
