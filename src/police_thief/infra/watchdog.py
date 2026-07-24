"""Watchdog: detects a frozen local main loop (FR-054, §8.4.2).

Independent of the Deadline Tracker (``infra/mcp_client.py``'s retry/timeout
logic, which watches the *remote* peer) — the Watchdog only watches this
peer's own heartbeat. Uses an injectable clock so tests never need real
sleeps.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import StrEnum

Clock = Callable[[], float]


class WatchdogStatus(StrEnum):
    ALIVE = "ALIVE"
    SHUTDOWN = "SHUTDOWN"


class Watchdog:
    """Call :meth:`heartbeat` from the main loop; call :meth:`check`
    periodically (e.g. from a separate thread) to detect staleness.
    """

    def __init__(
        self,
        timeout_sec: float,
        clock: Clock = time.monotonic,
        on_timeout: Callable[[], None] | None = None,
    ) -> None:
        self._timeout = timeout_sec
        self._clock = clock
        self._last_heartbeat = clock()
        self._on_timeout = on_timeout
        self._shutdown = False

    def heartbeat(self) -> None:
        self._last_heartbeat = self._clock()

    def check(self) -> WatchdogStatus:
        """§8.4.2's own reference logic: if the main loop appears frozen,
        persist state and shut down cleanly — never silently keep waiting.
        """
        if self._shutdown:
            return WatchdogStatus.SHUTDOWN
        elapsed = self._clock() - self._last_heartbeat
        if elapsed > self._timeout:
            self._shutdown = True
            if self._on_timeout is not None:
                self._on_timeout()
            return WatchdogStatus.SHUTDOWN
        return WatchdogStatus.ALIVE
