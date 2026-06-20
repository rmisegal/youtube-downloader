"""Construction helpers for the SDK: throttle/JS-runtime opts and the client.

Kept out of :mod:`ytdl.sdk.sdk` so that module stays small (Rule 8). These build
the ban-avoidance machinery from config: yt-dlp throttle opts, the detected JS
runtime, the persistent usage ledger, and the gatekeeper-routed client.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ytdl.infra.jsruntime import detect_runtime
from ytdl.infra.ytdlp_client import YtDlpClient
from ytdl.shared.config import ConfigManager
from ytdl.shared.gatekeeper import ApiGatekeeper
from ytdl.shared.queue import DownloadQueue
from ytdl.shared.rate_limit import RateLimiter
from ytdl.shared.throttle import ThrottlePolicy
from ytdl.shared.usage import UsageTracker

_REPO_ROOT = Path(__file__).resolve().parents[3]
_YT_LIMITS_KEY = "rate_limits.services.youtube"
_JS_RUNTIME_KEY = "network.js_runtime"
_USAGE_STATE_KEY = "usage_state_file"
_DEFAULT_USAGE_STATE = "config/.usage_state.json"
_USAGE_CAP_KEYS = (
    "requests_per_minute",
    "requests_per_hour",
    "requests_per_day",
    "requests_per_month",
)


def build_extra_opts(config: ConfigManager, rate_config: ConfigManager) -> dict[str, Any]:
    """Cross-cutting yt-dlp opts applied to every download (throttle + JS runtime)."""
    opts = ThrottlePolicy(rate_config).ydl_opts()
    runtimes = detect_runtime(config.get(_JS_RUNTIME_KEY, "auto"))
    if runtimes:
        opts["js_runtimes"] = runtimes
    return opts


def build_usage(rate_config: ConfigManager) -> UsageTracker:
    """Build the persistent per-minute/hour/day/month quota ledger from config."""
    limits = rate_config.get(_YT_LIMITS_KEY, {})
    caps = {k: limits.get(k) for k in _USAGE_CAP_KEYS if limits.get(k)}
    state = rate_config.get(_USAGE_STATE_KEY, _DEFAULT_USAGE_STATE)
    state_path = Path(state)
    if not state_path.is_absolute():
        state_path = _REPO_ROOT / state
    return UsageTracker(caps, state_path)


def build_client(rate_config: ConfigManager) -> YtDlpClient:
    """Assemble RateLimiter + DownloadQueue + UsageTracker + gatekeeper + client."""
    limits = rate_config.get(_YT_LIMITS_KEY, {})
    gatekeeper = ApiGatekeeper(
        RateLimiter(limits),
        DownloadQueue(rate_config),
        max_retries=limits.get("max_retries", 3),
        retry_after_seconds=limits.get("retry_after_seconds", 30),
        usage=build_usage(rate_config),
    )
    return YtDlpClient(gatekeeper)
