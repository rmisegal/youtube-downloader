"""API-key provider — Anthropic Messages API over ``urllib`` (no SDK dependency).

Used only when the user opts into ``--auth api`` (the default is CLI login). The key
is read from the environment (``.env``), never hardcoded, and redacted from errors.
Other vendors are a documented config hook for a later iteration.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from ytdl.shared.errors import LlmError

_ENDPOINT = "https://api.anthropic.com/v1/messages"


class AnthropicApiProvider:
    """Call the Anthropic Messages API with an API key from the environment."""

    def __init__(self, model: str, *, api_key_env: str = "ANTHROPIC_API_KEY",
                 timeout: int = 180, max_tokens: int = 4096) -> None:
        self._model = model
        self._key = os.environ.get(api_key_env)
        self._timeout = timeout
        self._max_tokens = max_tokens
        if not self._key:
            raise LlmError(f"{api_key_env} is not set (needed for --auth api)")

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """POST ``prompt`` to the Messages API; return the concatenated text blocks."""
        body: dict = {"model": self._model, "max_tokens": self._max_tokens,
                      "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = system
        req = urllib.request.Request(
            _ENDPOINT, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"x-api-key": self._key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310 - https
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise LlmError(f"Anthropic API call failed: {exc}") from exc
        return "".join(b.get("text", "") for b in data.get("content", [])).strip()
