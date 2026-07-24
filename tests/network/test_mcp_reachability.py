"""Networking tests — TEST-005 (reachability/retry half, split out of
test_mcp_transport.py to keep each file under 150 lines): the Deadline
Tracker's retry-then-give-up behavior and the startup reachability poll.
"""

from __future__ import annotations

import asyncio

import pytest

from police_thief.domain.models import Role
from police_thief.infra.mcp_client import MCPPeerClient, PeerUnreachableError
from police_thief.infra.mcp_server import build_server
from police_thief.infra.protocol import MessageType, ProtocolMessage, ProtocolResponse


def _always_accept(message: ProtocolMessage) -> ProtocolResponse:
    return ProtocolResponse(accepted=True)


def test_unreachable_peer_raises_after_retries():
    client = MCPPeerClient(
        "http://127.0.0.1:1/mcp",  # nothing listens here
        timeout_seconds=0.2,
        max_retries=1,
        retry_backoff_seconds=0.01,
    )
    message = ProtocolMessage(
        message_type=MessageType.COMMIT,
        game_id="g1",
        turn_number=0,
        sender_role=Role.POLICE,
        payload={},
    )
    with pytest.raises(PeerUnreachableError):
        asyncio.run(client.send(message))


def test_wait_until_reachable_succeeds_immediately_when_server_is_up():
    server = build_server("ping-peer", _always_accept)
    client = MCPPeerClient(server)
    assert asyncio.run(client.wait_until_reachable(max_wait_seconds=5.0, poll_interval=0.1))


def test_wait_until_reachable_times_out_for_an_unreachable_peer():
    client = MCPPeerClient("http://127.0.0.1:1/mcp", timeout_seconds=0.2)
    reachable = asyncio.run(client.wait_until_reachable(max_wait_seconds=0.3, poll_interval=0.1))
    assert not reachable
