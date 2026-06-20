"""Member -> ``MixSegment`` builder for the YAML playlist loader.

Resolves each member's ``file`` (relative -> ``source_folder``; URL -> download),
validates existence with the removable-drive guard (R56), and emits
``MixSegment``s (PRD-playlist §5.3 step 2). Split from ``loader.py`` to keep
both files ≤150 code lines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ytdl.constants import MEMBER_IMAGE
from ytdl.services.mixer.segment import MixSegment
from ytdl.services.playlist.model import Member, Playlist
from ytdl.shared.errors import PlaylistError

# Removable/network drives that may be unmounted (global drive-safety rule).
_REMOVABLE_DRIVES = ("D:", "H:")
# URL schemes a member ``file`` may carry (downloaded via the injected SDK).
_URL_SCHEMES = ("http://", "https://")


class Downloader(Protocol):
    """Minimal contract for the injected URL downloader (A1/R40)."""

    def download(self, url: str, *, output_dir: str) -> str:
        """Download ``url`` into ``output_dir`` and return the local file path."""
        ...


def build_segments(
    playlist: Playlist, *, downloader: Downloader | None = None
) -> list[MixSegment]:
    """Resolve + validate each member and build the ordered ``MixSegment`` list."""
    segments: list[MixSegment] = []
    for member in playlist.members:
        resolved = _resolve_file(member, playlist, downloader=downloader)
        segments.append(_to_segment(member, resolved))
    return segments


def _resolve_file(
    member: Member, playlist: Playlist, *, downloader: Downloader | None
) -> str:
    """Resolve a member ``file`` to a validated local path."""
    raw = member.file
    if _is_url(raw):
        return _download(raw, playlist, downloader=downloader)
    path = Path(raw)
    if _has_no_separator(raw):
        path = Path(playlist.metadata.source_folder) / raw
    return _validate_local(path)


def _is_url(value: str) -> bool:
    """True when ``value`` looks like an HTTP(S) URL."""
    return value.startswith(_URL_SCHEMES)


def _has_no_separator(value: str) -> bool:
    """True when ``value`` carries no path separator (bare file name)."""
    return "/" not in value and "\\" not in value


def _download(
    url: str, playlist: Playlist, *, downloader: Downloader | None
) -> str:
    """Download a URL member via the injected downloader (A1/R40)."""
    if downloader is None:
        raise PlaylistError(f"Member file is a URL but no downloader provided: {url}")
    output_dir = playlist.metadata.target_folder or "."
    return downloader.download(url, output_dir=output_dir)


def _validate_local(path: Path) -> str:
    """Apply the removable-drive guard (R56) and confirm the file exists."""
    _guard_removable(path)
    if not path.is_file():
        raise PlaylistError(f"Member file not found: {path}")
    return str(path)


def _guard_removable(path: Path) -> None:
    """Fail fast when ``path`` lives on an unmounted removable/network drive."""
    drive = path.drive.upper()
    if drive in _REMOVABLE_DRIVES and not Path(f"{drive}/").exists():
        raise PlaylistError(
            f"Drive not mounted: {drive} (connect the volume and retry)"
        )


def _to_segment(member: Member, resolved: str) -> MixSegment:
    """Map a resolved member onto a :class:`MixSegment`.

    For an image the on-screen duration comes from ``until - at`` (falling back to
    ``play_time``); video keeps its source in-point (``start``) + ``play_time``.
    """
    play = member.play_time
    if member.kind == MEMBER_IMAGE and member.at is not None and member.until is not None:
        play = max(0.0, member.until - member.at)
    return MixSegment(
        path=resolved,
        start=member.start_time,
        play_seconds=play,
        speed=member.playback_speed,
        resolution=member.resolution,
        subtitle=member.subtitle,
        effect=member.effect,
        kind=member.kind,
        transition=member.transition,
        direction=member.direction,
        at=member.at,
        until=member.until,
    )
