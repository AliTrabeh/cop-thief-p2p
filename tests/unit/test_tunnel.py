"""Unit tests for infra/tunnel.py — FR-006 (ngrok discovery half; the
TunnelHandle.stop()/start_tunnel-dispatch tests live in the sibling file
test_tunnel_dispatch.py, split out to keep each file under 150 lines).
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from _tunnel_helpers import FakeProcess, tunnels_response

from police_thief.infra.tunnel import TunnelError, TunnelHandle, TunnelProvider, start_ngrok_tunnel


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
        return tunnels_response([{"proto": "https", "public_url": "https://abc123.ngrok-free.app"}])

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
        return tunnels_response([])  # never any https tunnel

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
        # Use MockTransport + async-with so the client is closed before the event
        # loop shuts down — avoids hanging on Windows due to pending SSL resources.
        # The client is never actually called (process dies before any HTTP poll).
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _r: tunnels_response([]))
        ) as client:
            with pytest.raises(TunnelError, match="exited early"):
                await start_ngrok_tunnel(
                    8801,
                    which_fn=lambda _name: "/usr/bin/ngrok",
                    process_factory=lambda _args: fake_process,
                    http_client=client,
                    startup_timeout=1.0,
                )

    asyncio.run(run())
