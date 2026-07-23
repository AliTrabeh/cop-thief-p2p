"""The Gatekeeper rate-limiting pipeline (FR-055, NFR-006, §9.3.1-9.3.2).

Three stages, matching Figure 13 exactly: Quota Manager -> Token Bucket ->
DOS Detector, guarding every outgoing call (Gmail sends per FR-080..082, and
recommended for the FastMCP tool endpoint too). Uses an injectable clock
(defaulting to :func:`time.monotonic`) so tests never need real sleeps.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from police_thief.domain.models import RateLimiterGatekeeperConfig

Clock = Callable[[], float]


class GatekeeperVerdict(StrEnum):
    ALLOWED = "allowed"
    REJECTED_QUOTA_FULL = "rejected_quota_full"
    BLOCKED_NO_TOKEN = "blocked_no_token"
    LOCKED_ANOMALY = "locked_anomaly"


@dataclass
class TokenBucket:
    """``tokens <- min(C, tokens + r*dt)``, allow iff ``tokens >= 1`` (§9.3.2)."""

    capacity: float
    refill_rate: float
    clock: Clock = field(default=time.monotonic)
    tokens: float = field(init=False)
    _last: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = self.capacity
        self._last = self.clock()

    def _refill(self) -> None:
        now = self.clock()
        elapsed = now - self._last
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self._last = now

    def allow(self, cost: float = 1.0) -> bool:
        self._refill()
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


@dataclass
class QuotaManager:
    """A simple daily/per-window budget on the number of outgoing calls."""

    daily_limit: int
    clock: Clock = field(default=time.monotonic)
    _window_start: float = field(init=False)
    _count: int = field(init=False, default=0)
    _window_seconds: float = 86_400.0

    def __post_init__(self) -> None:
        self._window_start = self.clock()

    def allow(self) -> bool:
        now = self.clock()
        if now - self._window_start >= self._window_seconds:
            self._window_start = now
            self._count = 0
        if self._count >= self.daily_limit:
            return False
        self._count += 1
        return True


@dataclass
class DOSDetector:
    """Locks (circuit-breaker style) after ``burst_threshold`` calls arrive
    within ``burst_window_seconds`` of each other — an anomalous burst, not
    normal Gatekeeper-throttled traffic (§9.3.1 "DOS Detector").
    """

    burst_threshold: int
    burst_window_seconds: float
    clock: Clock = field(default=time.monotonic)
    _recent: list[float] = field(default_factory=list, init=False)
    _locked: bool = field(default=False, init=False)

    def check(self) -> bool:
        """Return ``True`` if traffic is clean; ``False`` once locked."""
        if self._locked:
            return False
        now = self.clock()
        self._recent = [t for t in self._recent if now - t <= self.burst_window_seconds]
        self._recent.append(now)
        if len(self._recent) > self.burst_threshold:
            self._locked = True
            return False
        return True

    def reset(self) -> None:
        self._locked = False
        self._recent.clear()


class Gatekeeper:
    """The full three-stage pipeline; call :meth:`admit` before every
    outgoing Gmail send (or, optionally, FastMCP tool call, NFR-006).
    """

    def __init__(self, config: RateLimiterGatekeeperConfig, clock: Clock = time.monotonic) -> None:
        self._quota = QuotaManager(daily_limit=config.queue_depth, clock=clock)
        self._bucket = TokenBucket(
            capacity=float(config.concurrent_requests),
            refill_rate=config.requests_per_minute / 60.0,
            clock=clock,
        )
        self._dos = DOSDetector(
            burst_threshold=config.requests_per_minute,
            burst_window_seconds=60.0,
            clock=clock,
        )

    def admit(self) -> GatekeeperVerdict:
        if not self._quota.allow():
            return GatekeeperVerdict.REJECTED_QUOTA_FULL
        if not self._bucket.allow():
            return GatekeeperVerdict.BLOCKED_NO_TOKEN
        if not self._dos.check():
            return GatekeeperVerdict.LOCKED_ANOMALY
        return GatekeeperVerdict.ALLOWED
