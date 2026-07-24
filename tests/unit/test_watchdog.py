"""Unit tests for infra/watchdog.py — FR-054."""

from __future__ import annotations

from police_thief.infra.watchdog import Watchdog, WatchdogStatus


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_watchdog_starts_alive():
    clock = FakeClock()
    dog = Watchdog(timeout_sec=10.0, clock=clock)
    assert dog.check() is WatchdogStatus.ALIVE


def test_watchdog_stays_alive_with_regular_heartbeats():
    clock = FakeClock()
    dog = Watchdog(timeout_sec=10.0, clock=clock)
    for _ in range(5):
        clock.advance(5.0)
        dog.heartbeat()
        assert dog.check() is WatchdogStatus.ALIVE


def test_watchdog_shuts_down_after_stale_period():
    clock = FakeClock()
    dog = Watchdog(timeout_sec=10.0, clock=clock)
    clock.advance(11.0)
    assert dog.check() is WatchdogStatus.SHUTDOWN


def test_watchdog_calls_on_timeout_exactly_once():
    clock = FakeClock()
    calls = []
    dog = Watchdog(timeout_sec=10.0, clock=clock, on_timeout=lambda: calls.append(1))
    clock.advance(11.0)
    dog.check()
    dog.check()
    dog.check()
    assert calls == [1]


def test_watchdog_stays_shutdown_permanently():
    clock = FakeClock()
    dog = Watchdog(timeout_sec=10.0, clock=clock)
    clock.advance(11.0)
    assert dog.check() is WatchdogStatus.SHUTDOWN
    dog.heartbeat()  # a heartbeat after shutdown does not resurrect it
    assert dog.check() is WatchdogStatus.SHUTDOWN
