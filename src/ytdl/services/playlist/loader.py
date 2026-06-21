"""YAML playlist loader: parse + validate -> model, build ``MixSegment``s.

Uses ``yaml.safe_load`` (Rule 13); raises ``PlaylistError`` on malformed/invalid
input — bad parse, non-dict, missing required keys, or an unsupported schema
version R55 (PRD-playlist §5.3, exit code 8). The member->segment builder lives
in ``loader_build.py`` to keep both files ≤150 code lines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ytdl.services.playlist.loader_build import Downloader, build_segments
from ytdl.services.playlist.model import (
    Leading,
    Member,
    Metadata,
    MixToggles,
    Output,
    Playlist,
    Sync,
)
from ytdl.services.playlist.track_model import TrackElement, Tracks
from ytdl.shared.errors import PlaylistError

# R55: schema versions this loader understands (PRD-playlist §5.2 ``version``).
SUPPORTED_PLAYLIST_VERSIONS: frozenset[str] = frozenset({"1.03", "1.04", "1.05"})

__all__ = ["SUPPORTED_PLAYLIST_VERSIONS", "build_segments", "load_playlist"]


def load_playlist(path: str | Path, *, downloader: Downloader | None = None) -> Playlist:
    """Read ``path``, validate it, and parse it into a :class:`Playlist`.

    ``downloader`` is accepted for API symmetry with :func:`build_segments`;
    parsing itself performs no I/O beyond reading the YAML file.
    """
    del downloader  # not needed for parsing; kept for a symmetric signature
    raw = _read(Path(path))
    data = _parse(raw)
    _validate_version(data)
    metadata = _build_metadata(data.get("metadata") or {})
    members = _build_members(data.get("members") or [])
    return Playlist(version=str(data["version"]), metadata=metadata, members=members)


def _read(path: Path) -> str:
    """Read the playlist file, mapping any I/O error to ``PlaylistError``."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PlaylistError(f"Cannot read playlist file: {path} ({exc})") from exc


def _parse(raw: str) -> dict[str, Any]:
    """Parse YAML with ``yaml.safe_load`` (Rule 13); require a mapping."""
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise PlaylistError(f"Malformed playlist YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise PlaylistError(f"Playlist must be a mapping, got {type(data).__name__}")
    if "version" not in data:
        raise PlaylistError("Playlist is missing required key: 'version'")
    return data


def _validate_version(data: dict[str, Any]) -> None:
    """R55: reject a ``version`` outside :data:`SUPPORTED_PLAYLIST_VERSIONS`."""
    version = str(data.get("version"))
    if version not in SUPPORTED_PLAYLIST_VERSIONS:
        raise PlaylistError(
            f"Unsupported playlist version {version!r}; "
            f"supported: {sorted(SUPPORTED_PLAYLIST_VERSIONS)}"
        )


def _build_metadata(raw: dict[str, Any]) -> Metadata:
    """Parse the ``metadata`` block into a :class:`Metadata` (schema defaults)."""
    output = Output(**_subset(raw.get("output"), Output))
    mix = MixToggles(**_subset(raw.get("mix"), MixToggles))
    leading = Leading(**_subset(raw.get("leading"), Leading))
    sync = Sync(**_subset(raw.get("sync"), Sync))
    return Metadata(
        source_folder=str(raw.get("source_folder", "")),
        target_folder=str(raw.get("target_folder", "")),
        output=output,
        mix=mix,
        leading=leading,
        sync=sync,
        tracks=_build_tracks(raw.get("tracks")),
        loop=bool(raw.get("loop", True)),
    )


def _build_tracks(raw: Any) -> Tracks:
    """Parse ``metadata.tracks`` (title/subtitle overlay tracks)."""
    if not isinstance(raw, dict):
        return Tracks()
    titles = tuple(_build_element(e) for e in raw.get("titles", []) if isinstance(e, dict))
    subs = tuple(_build_element(e) for e in raw.get("subtitles", []) if isinstance(e, dict))
    return Tracks(titles=titles, subtitles=subs)


def _build_element(raw: dict[str, Any]) -> TrackElement:
    """Parse one overlay-track text element."""
    return TrackElement(**_subset(raw, TrackElement))


def _build_members(raw: Any) -> list[Member]:
    """Parse + order playlist members by ``id`` (PRD-playlist §5.3 step 2)."""
    if not isinstance(raw, list):
        raise PlaylistError(f"'members' must be a list, got {type(raw).__name__}")
    members = [_build_member(item) for item in raw]
    return sorted(members, key=lambda member: member.id)


def _build_member(item: Any) -> Member:
    """Parse one member mapping into a :class:`Member`."""
    if not isinstance(item, dict):
        raise PlaylistError(f"Each member must be a mapping, got {type(item).__name__}")
    if "id" not in item or "file" not in item:
        raise PlaylistError(f"Member is missing required 'id'/'file': {item!r}")
    return Member(
        id=int(item["id"]),
        file=str(item["file"]),
        start_time=float(item.get("start_time", 0.0)),
        play_time=_opt_float(item.get("play_time")),
        playback_speed=float(item.get("playback_speed", 1.0)),
        resolution=str(item.get("resolution", "max")),
        subtitle=item.get("subtitle"),
        effect=str(item.get("effect", "fade")),
        kind=str(item.get("type", "video")),
        at=_opt_float(item.get("at")),
        until=_opt_float(item.get("until")),
        transition=str(item.get("transition", "random")),
        direction=str(item.get("direction", "")),
    )


def _opt_float(value: Any) -> float | None:
    """Coerce an optional numeric to ``float`` (``None`` stays ``None``)."""
    return None if value is None else float(value)


def _subset(raw: Any, cls: type) -> dict[str, Any]:
    """Keep only ``raw`` keys that are fields of dataclass ``cls``."""
    if not isinstance(raw, dict):
        return {}
    allowed = cls.__dataclass_fields__  # type: ignore[attr-defined]
    return {key: value for key, value in raw.items() if key in allowed}
