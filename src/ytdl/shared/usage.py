"""UsageTracker: persistent, cross-run request quota enforcement.

A JSON ledger of float epoch timestamps is kept on disk so that per-minute,
per-hour, per-day and per-month request caps are honoured *across* process
runs. This protects the YouTube account/IP from being throttled or blocked.

When a reservation would breach any enforced cap we RAISE
``RateLimitExceededError`` (stop) rather than hammering YouTube. The time
source is injected via ``time_fn`` so tests can drive a fake clock; nothing
here sleeps or touches the network.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from ytdl.shared.errors import RateLimitExceededError

_MINUTE_S = 60
_HOUR_S = 3600
_DAY_S = 86400
_MONTH_S = 2592000  # 30 days

# Maps each cap key to its window length in seconds.
_WINDOWS: dict[str, int] = {
    "requests_per_minute": _MINUTE_S,
    "requests_per_hour": _HOUR_S,
    "requests_per_day": _DAY_S,
    "requests_per_month": _MONTH_S,
}


class UsageTracker:
    """Enforce persistent request quotas backed by a JSON timestamp ledger."""

    def __init__(
        self,
        caps: dict[str, int],
        state_path: str | Path,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        """Build a tracker.

        Args:
            caps: Subset of ``requests_per_{minute,hour,day,month}``. Entries
                that are missing, ``None`` or ``<= 0`` are ignored (unlimited).
            state_path: Path to the JSON ledger file (created on first write).
            time_fn: Zero-arg epoch-seconds clock; injected for testability.
        """
        self._state_path = Path(state_path)
        self._time_fn = time_fn
        # Only keep enforced caps: positive ints with a known window.
        self._caps: dict[str, int] = {
            key: int(caps[key])
            for key in _WINDOWS
            if caps.get(key) is not None and int(caps[key]) > 0
        }

    def _load(self) -> list[float]:
        """Load the ledger, tolerating a missing or corrupt file."""
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            return []
        if not isinstance(raw, list):
            return []
        return [float(ts) for ts in raw if isinstance(ts, (int, float))]

    def _save(self, ledger: list[float]) -> None:
        """Persist the ledger atomically (write to temp, then replace)."""
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._state_path.with_suffix(self._state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(ledger), encoding="utf-8")
        tmp.replace(self._state_path)

    def _count_within(self, ledger: list[float], now: float, window: int) -> int:
        """Number of ledger timestamps within ``window`` seconds of ``now``."""
        cutoff = now - window
        return sum(1 for ts in ledger if ts > cutoff)

    def _reset_hint(self, ledger: list[float], now: float, window: int) -> int:
        """Seconds until the oldest in-window timestamp leaves ``window``."""
        in_window = sorted(ts for ts in ledger if ts > now - window)
        if not in_window:
            return 0
        return max(int((in_window[0] + window) - now), 0)

    def counts(self) -> dict[str, int]:
        """Return current request counts keyed by enforced cap name."""
        ledger = self._load()
        now = self._time_fn()
        return {
            key: self._count_within(ledger, now, _WINDOWS[key]) for key in self._caps
        }

    def reserve(self) -> None:
        """Reserve one request slot or raise if any enforced cap is hit.

        On success the current timestamp is appended and persisted. When a cap
        would be exceeded nothing is recorded and ``RateLimitExceededError`` is
        raised, naming the window, the cap and the approximate reset hint.
        """
        ledger = self._load()
        now = self._time_fn()
        if not self._caps:
            ledger.append(now)
            self._save(ledger)
            return

        horizon = now - max(_WINDOWS[key] for key in self._caps)
        ledger = [ts for ts in ledger if ts > horizon]

        for key, cap in self._caps.items():
            window = _WINDOWS[key]
            count = self._count_within(ledger, now, window)
            if count >= cap:
                hint = self._reset_hint(ledger, now, window)
                raise RateLimitExceededError(
                    f"Usage cap reached for {key} ({count}/{cap} in "
                    f"{window}s window); retry in ~{hint}s to protect the "
                    "account from being blocked."
                )

        ledger.append(now)
        self._save(ledger)
