"""Networking tests — TEST-005. Uses FastMCP's real client/server stack over
an in-process transport (a genuine MCP protocol round trip, not a mock of
our own code — the "real local communication layer" the testing strategy
requires), so these tests exercise real (de)serialization, tool dispatch,
and error propagation without needing an actual open socket in CI.
"""

from __future__ import annotations

import asyncio

import pytest

from police_thief.domain.models import Role
from police_thief.infra.mcp_client import MCPPeerClient, PeerUnreachableError
from police_thief.infra.mcp_server import build_server
from police_thief.infra.protocol import MessageType, ProtocolMessage, ProtocolResponse, RejectReason


def _always_accept(message: ProtocolMessage) -> ProtocolResponse:
    return ProtocolResponse(accepted=True)


def _always_reject_illegal(message: ProtocolMessage) -> ProtocolResponse:
    return ProtocolResponse(accepted=False, reason=RejectReason.ILLEGAL_MOVE)


def test_successful_round_trip():
    server = build_server("test-peer", _always_accept)
    client = MCPPeerClient(server)
    message = ProtocolMessage(
        message_type=MessageType.COMMIT,
        game_id="g1",
        turn_number=0,
        sender_role=Role.POLICE,
        payload={"h_commit": "abc123"},
    )
    response = asyncio.run(client.send(message))
    assert response.accepted


def test_handler_rejection_is_returned_not_raised():
    server = build_server("test-peer", _always_reject_illegal)
    client = MCPPeerClient(server)
    message = ProtocolMessage(
        message_type=MessageType.REVEAL,
        game_id="g1",
        turn_number=0,
        sender_role=Role.THIEF,
        payload={"move": "N"},
    )
    response = asyncio.run(client.send(message))
    assert not response.accepted
    assert response.reason is RejectReason.ILLEGAL_MOVE


def test_duplicate_turn_is_rejected_idempotently():
    server = build_server("test-peer", _always_accept)
    client = MCPPeerClient(server)
    message = ProtocolMessage(
        message_type=MessageType.COMMIT,
        game_id="g1",
        turn_number=0,
        sender_role=Role.POLICE,
        payload={"h_commit": "abc123"},
    )
    first = asyncio.run(client.send(message))
    second = asyncio.run(client.send(message))
    assert first.accepted
    assert not second.accepted
    assert second.reason is RejectReason.DUPLICATE


def test_stale_turn_is_rejected():
    server = build_server("test-peer", _always_accept)
    client = MCPPeerClient(server)
    later = ProtocolMessage(
        message_type=MessageType.COMMIT,
        game_id="g1",
        turn_number=5,
        sender_role=Role.POLICE,
        payload={},
    )
    stale = ProtocolMessage(
        message_type=MessageType.COMMIT,
        game_id="g1",
        turn_number=2,
        sender_role=Role.POLICE,
        payload={},
    )
    assert asyncio.run(client.send(later)).accepted
    stale_response = asyncio.run(client.send(stale))
    assert not stale_response.accepted
    assert stale_response.reason is RejectReason.STALE_TURN


def test_malformed_payload_is_rejected_not_a_server_crash():
    server = build_server("test-peer", _always_accept)

    async def send_raw() -> dict:
        from fastmcp import Client

        async with Client(server) as raw_client:
            result = await raw_client.call_tool(
                "submit_message", {"message": {"not": "a valid message"}}
            )
            return result.data

    data = asyncio.run(send_raw())
    assert data["accepted"] is False
    assert data["reason"] == RejectReason.MALFORMED.value


def test_oversized_payload_is_rejected():
    server = build_server("test-peer", _always_accept, max_payload_fields=2)
    client = MCPPeerClient(server)
    message = ProtocolMessage(
        message_type=MessageType.COMMIT,
        game_id="g1",
        turn_number=0,
        sender_role=Role.POLICE,
        payload={"a": "1", "b": "2", "c": "3"},
    )
    response = asyncio.run(client.send(message))
    assert not response.accepted
    assert response.reason is RejectReason.MALFORMED


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
