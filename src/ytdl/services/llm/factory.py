"""``build_provider`` — pick a vendor + auth mode (default: Claude via CLI login).

Config-driven (``setup.json`` ``llm.*`` with safe fallbacks): in ``cli`` mode it builds
a :class:`CliProvider` for the vendor's CLI (scrubbing its API-key env vars); in ``api``
mode it builds the API-key provider. No hardcoded secrets — keys live in ``.env``.
"""

from __future__ import annotations

from typing import Any

from ytdl.services.llm.api_provider import AnthropicApiProvider
from ytdl.services.llm.cli_provider import CliProvider
from ytdl.services.llm.provider import LlmProvider
from ytdl.shared.config import ConfigManager
from ytdl.shared.errors import LlmError

DEFAULT_VENDOR = "claude"
DEFAULT_AUTH = "cli"

# Per-vendor CLI defaults (overridable in setup.json llm.providers.<vendor>.*).
_CLI_DEFAULTS: dict[str, dict[str, Any]] = {
    "claude": {"executable": "claude", "args": ["-p"],
               "strip": ["ANTHROPIC_API_KEY", "CLAUDECODE", "ANTHROPIC_BASE_URL",
                         "ANTHROPIC_AUTH_TOKEN", "API_TIMEOUT_MS"]},
    "gemini": {"executable": "gemini", "args": [], "strip": ["GEMINI_API_KEY", "GOOGLE_API_KEY"]},
}


def build_provider(
    vendor: str = DEFAULT_VENDOR, auth: str = DEFAULT_AUTH, config: ConfigManager | None = None,
) -> LlmProvider:
    """Return an :class:`LlmProvider` for ``vendor``/``auth`` (default claude/cli)."""
    cfg = config or ConfigManager(file_name="setup.json")
    if auth == "api":
        if vendor != "claude":
            raise LlmError(f"--auth api is not wired for vendor '{vendor}' yet (use cli login)")
        return AnthropicApiProvider(cfg.get("llm.api.model", "claude-opus-4-8"))
    defaults = _CLI_DEFAULTS.get(vendor, {"executable": vendor, "args": [], "strip": []})
    base = f"llm.providers.{vendor}"
    return CliProvider(
        executable=cfg.get(f"{base}.executable", defaults["executable"]),
        args=cfg.get(f"{base}.args", defaults["args"]),
        strip_env_keys=cfg.get(f"{base}.strip_env_keys", defaults["strip"]),
    )
