"""Unit tests for infra/tunnel.py — FR-006.

Every external dependency (binary lookup, subprocess creation, HTTP calls)
is faked/injected here; no real ngrok binary or network access is used.
"""

from __future__ import annotations

import asyncio
import subprocess

import httpx
import pytest

from police_thief.infra.tunnel import (
    TunnelError,
    TunnelHandle,
    TunnelProvider,
    start_ngrok_tunnel,
    start_tunnel,
)


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


def _tunnels_response(tunnels: list[dict[str, str]]) -> httpx.Response:
    return httpx.Response(200, json={"tunnels": tunnels})


def test_start_ngrok_tunnel_raises_when_binary_missing():
    async def run() -> None:
        with pytest.raises(TunnelError, match="not found on PATH"):
            await start_ngrok_tunnel(8801, which_fn=lambda _name: None)

    asyncio.run(run())


def test_start_ngrok_tunnel_discovers_public_url():
    fake_process = FakeProcess(exit_code=None)
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return _tunnels_response(
            [{"proto": "https", "public_url": "https://abc123.ngrok-free.app"}]
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def run() -> TunnelHandle:
        return await start_ngrok_tunnel(
            8801,
            which_fn=lambda _name: "/usr/bin/ngrok",
            process_factory=lambda _args: fake_process,
            http_client=client,
            poll_interval=0.01,
        )

    handle = asyncio.run(run())
    assert handle.provider is TunnelProvider.NGROK
    assert handle.public_url == "https://abc123.ngrok-free.app"
    assert call_count >= 1


def test_start_ngrok_tunnel_times_out_if_no_tunnel_ever_appears():
    fake_process = FakeProcess(exit_code=None)

    def handler(request: httpx.Request) -> httpx.Response:
        return _tunnels_response([])  # never any https tunnel

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def run() -> None:
        with pytest.raises(TunnelError, match="did not expose"):
            await start_ngrok_tunnel(
                8801,
                which_fn=lambda _name: "/usr/bin/ngrok",
                process_factory=lambda _args: fake_process,
                http_client=client,
                startup_timeout=0.05,
                poll_interval=0.01,
            )

    asyncio.run(run())
    assert fake_process.terminated


def test_start_ngrok_tunnel_raises_if_process_exits_early():
    fake_process = FakeProcess(exit_code=1)  # already dead before the first poll

    async def run() -> None:
        with pytest.raises(TunnelError, match="exited early"):
            await start_ngrok_tunnel(
                8801,
                which_fn=lambda _name: "/usr/bin/ngrok",
                process_factory=lambda _args: fake_process,
                http_client=httpx.AsyncClient(),
                startup_timeout=1.0,
            )

    asyncio.run(run())


def test_tunnel_handle_stop_terminates_a_running_process():
    fake_process = FakeProcess(exit_code=None)
    handle = TunnelHandle(
        provider=TunnelProvider.NGROK, public_url="https://x", _process=fake_process
    )
    handle.stop()
    assert fake_process.terminated


def test_tunnel_handle_stop_is_a_noop_if_already_exited():
    fake_process = FakeProcess(exit_code=0)
    handle = TunnelHandle(
        provider=TunnelProvider.NGROK, public_url="https://x", _process=fake_process
    )
    handle.stop()
    assert not fake_process.terminated


def test_tunnel_handle_stop_kills_if_terminate_times_out():
    fake_process = FakeProcess(exit_code=None)
    fake_process._wait_raises_once = True
    handle = TunnelHandle(
        provider=TunnelProvider.NGROK, public_url="https://x", _process=fake_process
    )
    handle.stop()
    assert fake_process.terminated
    assert fake_process.killed


def test_start_tunnel_none_returns_none():
    async def run() -> TunnelHandle | None:
        return await start_tunnel("none", 8801)

    assert asyncio.run(run()) is None


def test_start_tunnel_manual_requires_a_url():
    async def run() -> None:
        with pytest.raises(TunnelError, match="manual_public_url"):
            await start_tunnel("manual", 8801)

    asyncio.run(run())


def test_start_tunnel_manual_returns_the_given_url():
    async def run() -> TunnelHandle | None:
        return await start_tunnel("manual", 8801, manual_public_url="https://my-tunnel.example.com")

    handle = asyncio.run(run())
    assert handle is not None
    assert handle.provider is TunnelProvider.MANUAL
    assert handle.public_url == "https://my-tunnel.example.com"


def test_start_tunnel_rejects_unknown_provider():
    async def run() -> None:
        with pytest.raises(ValueError):
            await start_tunnel("carrier-pigeon", 8801)

    asyncio.run(run())
