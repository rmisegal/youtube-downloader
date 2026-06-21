"""Unit tests for the Prompter and the MovieWizard (scripted I/O)."""

from __future__ import annotations

from ytdl.services.pipeline.prompter import Prompter
from ytdl.services.pipeline.wizard import MovieWizard


def _prompter(answers):
    it = iter(answers)
    out = []
    return Prompter(input_fn=lambda _p: next(it), print_fn=out.append), out


def test_ask_defaults_and_strip() -> None:
    p, _ = _prompter(["  hi  ", ""])
    assert p.ask("q") == "hi"
    assert p.ask("q", default="d") == "d"  # blank → default


def test_ask_path_strips_quotes() -> None:
    p, _ = _prompter(['"C:\\a b\\song.mp3"'])
    assert p.ask_path("file") == "C:\\a b\\song.mp3"


def test_ask_int_and_eof() -> None:
    p, _ = _prompter(["notnum"])
    assert p.ask_int("n", default=24) == 24

    def raise_eof(_p):
        raise EOFError

    assert Prompter(input_fn=raise_eof).ask("q", default="x") == "x"


def test_choose_valid_and_invalid() -> None:
    p, _ = _prompter(["2"])
    assert p.choose("pick", ["a", "b", "c"], default="a") == "b"
    p2, _ = _prompter(["9"])
    assert p2.choose("pick", ["a", "b"], default="a") == "a"  # out of range → default


def test_wizard_builds_config_with_leading() -> None:
    answers = [
        "a space trip",                 # idea
        "C:\\song.mp3",                 # leading
        "C:\\out",                      # output
        "8",                            # scenes
        "2",                            # sync style choice (dj_party)
        "1",                            # cut rhythm choice (bar)
        "Space",                        # topic
        "rockets and stars",            # description
        "epic",                         # vibe
        "1",                            # vendor (claude)
        "1",                            # auth (cli)
    ]
    p, _ = _prompter(answers)
    cfg = MovieWizard(p).run()
    assert cfg.leading == "C:\\song.mp3" and cfg.scene_target == 8
    assert cfg.sync_target == "dj_party" and cfg.mode == "bar"
    assert cfg.topic == "Space" and cfg.vibe == "epic"
    assert cfg.llm_vendor == "claude" and cfg.llm_auth == "cli"


def test_wizard_no_leading_skips_sync() -> None:
    answers = ["idea", "", "C:\\out", "5", "topic", "desc", "vibe", "1", "1"]
    p, _ = _prompter(answers)
    cfg = MovieWizard(p).run()
    assert not cfg.has_leading and cfg.scene_target == 5 and cfg.topic == "topic"
