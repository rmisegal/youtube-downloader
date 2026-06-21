"""CLI-login provider — shell out to a vendor CLI (default: ``claude -p``).

Adapted from basic-clis ``BaseCliProvider``: the prompt is piped to the vendor CLI in
print/headless mode, and the configured keys (``ANTHROPIC_API_KEY``/``CLAUDECODE``/…)
are **stripped from the child env** so the CLI uses the subscription LOGIN, not an API
key (the user's explicit requirement). No network/SDK dependency — just ``subprocess``.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence

from ytdl.shared.errors import LlmError


class CliProvider:
    """Run prompts through a vendor CLI tool using its subscription login."""

    def __init__(
        self, executable: str, args: Sequence[str], strip_env_keys: Sequence[str],
        *, timeout: int = 180,
    ) -> None:
        self._exe = executable
        self._args = list(args)
        self._strip = list(strip_env_keys)
        self._timeout = timeout

    def _env(self) -> dict[str, str]:
        """A copy of the environment with the API-key vars removed (forces CLI login)."""
        return {k: v for k, v in os.environ.items() if k not in self._strip}

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Pipe ``prompt`` to ``<exe> <args>`` (stdin) and return its stdout text."""
        text = f"{system}\n\n{prompt}" if system else prompt
        try:
            result = subprocess.run(  # noqa: S603 - exe/args come from trusted config
                [self._exe, *self._args], input=text, capture_output=True, text=True,
                timeout=self._timeout, encoding="utf-8", errors="replace", env=self._env(),
            )
        except FileNotFoundError as exc:
            raise LlmError(f"LLM CLI '{self._exe}' not found on PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise LlmError(f"LLM CLI '{self._exe}' timed out after {self._timeout}s") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "unknown error").strip()
            raise LlmError(f"LLM CLI '{self._exe}' failed: {detail[:300]}")
        return result.stdout.strip()
