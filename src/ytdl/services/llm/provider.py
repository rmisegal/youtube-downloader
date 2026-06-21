"""``LlmProvider`` — the one contract every vendor/auth-mode implements."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LlmProvider(ABC):
    """Send a prompt to a model and get plain text back."""

    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return the model's text reply to ``prompt`` (with optional ``system``)."""
