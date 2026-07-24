"""Shared fakes for the tunnel unit tests (test_tunnel.py,
test_tunnel_dispatch.py) — not itself a test file (no ``test_`` prefix, so
pytest doesn't collect it), split out purely to keep each test file under
150 lines. Every external dependency (binary lookup, subprocess creation,
HTTP calls) is faked/injected here; no real ngrok binary or network access
is used anywhere in these tests.
"""

from __future__ import annotations

import subprocess

import httpx


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeProcess:
    """Stands in for subprocess.Popen in tests."""

    def __init__(self, exit_code: int | None = None) -> None:
        self.returncode = exit_code
        self.terminated = False
        self.killed = False
        self._wait_raises_once = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def wait(self, timeout: float | None = None) -> int:
        if self._wait_raises_once:
            self._wait_raises_once = False
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout or 0)
        return self.returncode or 0


def tunnels_response(tunnels: list[dict[str, str]]) -> httpx.Response:
    return httpx.Response(200, json={"tunnels": tunnels})
