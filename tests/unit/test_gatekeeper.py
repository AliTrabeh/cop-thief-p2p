"""Unit tests for infra/gatekeeper.py — FR-055, NFR-006, TEST-005."""

from __future__ import annotations

from police_thief.infra.gatekeeper import (
    DOSDetector,
    Gatekeeper,
    GatekeeperVerdict,
    QuotaManager,
    TokenBucket,
)


class FakeClock:
    """A controllable clock so tests never need real sleeps."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_token_bucket_starts_full_and_drains():
    clock = FakeClock()
    bucket = TokenBucket(capacity=2, refill_rate=1.0, clock=clock)
    assert bucket.allow()
    assert bucket.allow()
    assert not bucket.allow()  # empty


def test_token_bucket_refills_over_time():
    clock = FakeClock()
    bucket = TokenBucket(capacity=2, refill_rate=1.0, clock=clock)
    assert bucket.allow()
    assert bucket.allow()
    assert not bucket.allow()
    clock.advance(1.0)  # 1 token/sec refill
    assert bucket.allow()
    assert not bucket.allow()


def test_token_bucket_never_exceeds_capacity():
    clock = FakeClock()
    bucket = TokenBucket(capacity=2, refill_rate=1.0, clock=clock)
    clock.advance(1000.0)  # huge idle gap
    assert bucket.tokens == 2  # not refilled yet, refill only recomputed on allow()
    assert bucket.allow()
    assert bucket.tokens == 1  # still capped, one token consumed


def test_quota_manager_enforces_daily_limit():
    clock = FakeClock()
    quota = QuotaManager(daily_limit=2, clock=clock)
    assert quota.allow()
    assert quota.allow()
    assert not quota.allow()


def test_quota_manager_resets_after_window():
    clock = FakeClock()
    quota = QuotaManager(daily_limit=1, clock=clock)
    assert quota.allow()
    assert not quota.allow()
    clock.advance(86_400.0)
    assert quota.allow()


def test_dos_detector_locks_on_burst():
    clock = FakeClock()
    detector = DOSDetector(burst_threshold=3, burst_window_seconds=10.0, clock=clock)
    assert detector.check()
    assert detector.check()
    assert detector.check()
    assert not detector.check()  # 4th call within the window trips the lock
    assert not detector.check()  # stays locked, doesn't self-heal without reset()


def test_dos_detector_reset_clears_lock():
    clock = FakeClock()
    detector = DOSDetector(burst_threshold=1, burst_window_seconds=10.0, clock=clock)
    assert detector.check()
    assert not detector.check()
    detector.reset()
    assert detector.check()


def test_gatekeeper_pipeline_allows_normal_traffic(game_config):
    clock = FakeClock()
    gk = Gatekeeper(game_config.rate_limiter_gatekeeper, clock=clock)
    assert gk.admit() is GatekeeperVerdict.ALLOWED


def test_gatekeeper_pipeline_blocks_once_bucket_is_empty(game_config):
    clock = FakeClock()
    gk = Gatekeeper(game_config.rate_limiter_gatekeeper, clock=clock)
    concurrent = game_config.rate_limiter_gatekeeper.concurrent_requests
    for _ in range(concurrent):
        assert gk.admit() is GatekeeperVerdict.ALLOWED
    assert gk.admit() is GatekeeperVerdict.BLOCKED_NO_TOKEN
