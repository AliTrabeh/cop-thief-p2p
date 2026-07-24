"""Unit tests for infra/tunnel.py — FR-006 (TunnelHandle.stop() and
start_tunnel provider-dispatch half, split out of test_tunnel.py to keep
each file under 150 lines).
"""

from __future__ import annotations

import asyncio

import pytest
from _tunnel_helpers import FakeProcess

from police_thief.infra.tunnel import TunnelError, TunnelHandle, TunnelProvider, start_tunnel


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
