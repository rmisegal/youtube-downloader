"""``Prompter`` — a small, testable interactive-prompt helper (GtaiGrader pattern).

I/O is injected (``input_fn``/``print_fn``) so wizards are unit-testable and degrade to
defaults headlessly (EOF → default). ``ask_path`` strips quotes off pasted Windows
paths; ``choose`` renders a plain numbered menu.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence


class Prompter:
    """Read typed answers with sensible defaults; no third-party TUI dependency."""

    def __init__(self, input_fn: Callable[[str], str] = input,
                 print_fn: Callable[[str], None] = print) -> None:
        self._input = input_fn
        self._print = print_fn

    def say(self, message: str) -> None:
        """Print an informational line."""
        self._print(message)

    def ask(self, prompt: str, *, default: str = "") -> str:
        """Ask for a line; blank or EOF → ``default``."""
        suffix = f" [{default}]" if default else ""
        try:
            raw = self._input(f"{prompt}{suffix}: ").strip()
        except EOFError:
            return default
        return raw or default

    def ask_path(self, prompt: str, *, default: str = "") -> str:
        """Ask for a path, stripping surrounding quotes from a pasted value."""
        return self.ask(prompt, default=default).strip().strip('"').strip("'")

    def ask_int(self, prompt: str, *, default: int) -> int:
        """Ask for an integer; non-numeric → ``default``."""
        try:
            return int(self.ask(prompt, default=str(default)))
        except (TypeError, ValueError):
            return default

    def choose(self, prompt: str, options: Sequence[str], *, default: str) -> str:
        """Render a numbered menu and return the chosen option (bad input → default)."""
        self._print(prompt)
        for i, opt in enumerate(options, 1):
            self._print(f"  {i}) {opt}")
        start = str(list(options).index(default) + 1) if default in options else "1"
        try:
            idx = int(self.ask("choice #", default=start)) - 1
            return options[idx] if 0 <= idx < len(options) else default
        except (TypeError, ValueError):
            return default
