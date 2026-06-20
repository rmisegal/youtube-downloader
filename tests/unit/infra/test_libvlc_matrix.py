"""Unit tests for ``LibVlcPlayerMatrix`` (Option 2 — dual-libVLC gapless + audio xfade).

A FAKE ``vlc`` module is injected (``Instance``/``MediaPlayer``/``Media`` mocks), the
clock is a fake counter, and ``sleep`` is a no-op — so NO real vlc and NO real timing.
The active player's ``get_time()`` advances with each poll so the wait loop terminates
deterministically.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ytdl.infra.playback.libvlc_matrix import LibVlcPlayerMatrix


class FakePlayer:
    """Records calls; ``get_time`` walks a scripted list of ms positions."""

    def __init__(self) -> None:
        self.media = None
        self.set_time_calls: list[int] = []
        self.volume_calls: list[int] = []
        self.played = 0
        self.stopped = 0
        self._times: list[int] = [0]
        self._idx = 0

    def script_times(self, seconds: list[float]) -> None:
        self._times = [int(s * 1000) for s in seconds]
        self._idx = 0

    def set_media(self, media: object) -> None:
        self.media = media

    def set_time(self, ms: int) -> None:
        self.set_time_calls.append(ms)

    def set_volume(self, vol: int) -> None:
        self.volume_calls.append(vol)

    def play(self) -> None:
        self.played += 1

    def stop(self) -> None:
        self.stopped += 1

    def get_time(self) -> int:
        ms = self._times[min(self._idx, len(self._times) - 1)]
        self._idx += 1
        return ms


class FakeInstance:
    def __init__(self, players: list[FakePlayer]) -> None:
        self._players = players
        self._n = 0

    def media_player_new(self) -> FakePlayer:
        player = self._players[self._n]
        self._n += 1
        return player


def make_vlc(players: list[FakePlayer]) -> SimpleNamespace:
    """Build a fake ``vlc`` module exposing ``Instance`` and ``Media``."""
    instance = FakeInstance(players)
    return SimpleNamespace(
        Instance=lambda *a, **k: instance,
        Media=lambda path: SimpleNamespace(path=path),
    )


@pytest.fixture
def players() -> list[FakePlayer]:
    return [FakePlayer(), FakePlayer()]


def make_matrix(players: list[FakePlayer], **kw: object) -> LibVlcPlayerMatrix:
    kw.setdefault("crossfade", 3.0)
    return LibVlcPlayerMatrix(
        vlc_module=make_vlc(players),
        clock=lambda: 0.0,
        sleep=lambda _s: None,
        **kw,  # type: ignore[arg-type]
    )


def test_prepare_next_seeks_to_in_point(players: list[FakePlayer]) -> None:
    matrix = make_matrix(players, target_start_time=10.0)
    matrix._prepare_next(matrix.player_b, "next.mp4")
    # in-point: target_start_time (10s) -> set_time(10000) ms
    assert players[1].set_time_calls == [10000]
    assert players[1].volume_calls[0] == 0  # muted initially


def test_default_mix_point_is_duration_minus_crossfade(
    players: list[FakePlayer],
) -> None:
    matrix = make_matrix(players, source_mix_time=None, crossfade=3.0)
    # source_duration=100, crossfade=3 -> mix begins at 97
    assert matrix._mix_point(100.0) == 97.0


def test_explicit_source_mix_time_overrides(players: list[FakePlayer]) -> None:
    matrix = make_matrix(players, source_mix_time=30.0)
    assert matrix._mix_point(100.0) == 30.0


def test_wait_loop_terminates_at_mix_point(players: list[FakePlayer]) -> None:
    matrix = make_matrix(players, source_mix_time=30.0)
    active, nxt = players[0], players[1]
    # position climbs 10 -> 20 -> 31 (>=30) so the loop terminates deterministically
    active.script_times([10.0, 20.0, 31.0, 31.0])
    matrix.crossfade_pair(active, nxt, source_duration=100.0)
    assert active.stopped == 1


def test_crossfade_ramps_volumes_and_swaps_decks(
    players: list[FakePlayer],
) -> None:
    matrix = make_matrix(players, source_mix_time=97.0, crossfade=3.0)
    active, nxt = players[0], players[1]
    active.script_times([97.0, 97.0])
    result = matrix.crossfade_pair(active, nxt, source_duration=100.0)

    # active ramps DOWN toward 0, next ramps UP toward 100
    assert active.volume_calls[0] == 100  # set to full before play
    ramp_down = active.volume_calls[1:]
    assert ramp_down[-1] == 0
    assert ramp_down == sorted(ramp_down, reverse=True)
    assert nxt.volume_calls[-1] == 100
    assert nxt.volume_calls == sorted(nxt.volume_calls)

    assert nxt.played >= 1  # nxt.play() called
    assert active.stopped == 1  # then active.stop()
    assert result is nxt  # next deck becomes active


def test_play_sequence_alternates_decks(players: list[FakePlayer]) -> None:
    matrix = make_matrix(players, source_mix_time=5.0, crossfade=1.0)
    for p in players:
        p.script_times([5.0, 5.0])
    matrix.play_sequence(["a.mp4", "b.mp4"], [10.0])
    # both decks were loaded (set_media called) and the handoff stopped deck A
    assert players[0].media is not None
    assert players[1].media is not None
    assert players[0].stopped == 1


def test_play_sequence_empty_is_noop(players: list[FakePlayer]) -> None:
    matrix = make_matrix(players)
    matrix.play_sequence([], [])
    assert players[0].played == 0


def test_media_player_shortcut_when_no_instance() -> None:
    created: list[FakePlayer] = []

    def media_player() -> FakePlayer:
        p = FakePlayer()
        created.append(p)
        return p

    fake = SimpleNamespace(MediaPlayer=media_player, Media=lambda p: p)
    matrix = LibVlcPlayerMatrix(
        vlc_module=fake, clock=lambda: 0.0, sleep=lambda _s: None, crossfade=3.0
    )
    assert matrix.player_a is created[0]
    assert matrix.player_b is created[1]
