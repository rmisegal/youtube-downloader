"""Unit tests for the multi-vendor LLM auth layer (CLI-login + API key)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ytdl.services.llm.cli_provider import CliProvider
from ytdl.services.llm.factory import build_provider
from ytdl.shared.config import ConfigManager
from ytdl.shared.errors import LlmError


def test_cli_provider_scrubs_api_key_from_child_env(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    monkeypatch.setenv("KEEP_ME", "1")
    prov = CliProvider("claude", ["-p"], ["ANTHROPIC_API_KEY"])
    captured = {}

    def fake_run(argv, **kw):  # noqa: ANN001, ANN003
        captured["argv"] = argv
        captured["env"] = kw["env"]
        captured["input"] = kw["input"]
        return SimpleNamespace(returncode=0, stdout="hello\n", stderr="")

    with patch("ytdl.services.llm.cli_provider.subprocess.run", fake_run):
        out = prov.complete("hi", system="be brief")
    assert out == "hello"
    assert captured["argv"] == ["claude", "-p"]
    assert "ANTHROPIC_API_KEY" not in captured["env"]  # scrubbed → uses CLI login
    assert captured["env"]["KEEP_ME"] == "1"
    assert captured["input"].startswith("be brief")  # system prepended


def test_cli_provider_raises_on_failure() -> None:
    prov = CliProvider("claude", ["-p"], [])
    with patch("ytdl.services.llm.cli_provider.subprocess.run",
               return_value=SimpleNamespace(returncode=1, stdout="", stderr="boom")), \
            pytest.raises(LlmError):
        prov.complete("hi")


def test_cli_provider_missing_executable() -> None:
    prov = CliProvider("nope", [], [])
    with patch("ytdl.services.llm.cli_provider.subprocess.run", side_effect=FileNotFoundError), \
            pytest.raises(LlmError):
        prov.complete("hi")


def test_factory_default_is_claude_cli() -> None:
    cfg = ConfigManager(data={"version": "1.06"})
    prov = build_provider(config=cfg)
    assert isinstance(prov, CliProvider)
    assert "ANTHROPIC_API_KEY" in prov._strip  # default claude scrub list


def test_factory_api_mode_needs_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = ConfigManager(data={"version": "1.06"})
    with pytest.raises(LlmError):
        build_provider(vendor="claude", auth="api", config=cfg)


def test_factory_api_unsupported_vendor() -> None:
    cfg = ConfigManager(data={"version": "1.06"})
    with pytest.raises(LlmError):
        build_provider(vendor="openai", auth="api", config=cfg)
