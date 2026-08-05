"""Networking tests — TEST-005. Uses FastMCP's real client/server stack over
an in-process transport (a genuine MCP protocol round trip, not a mock of
our own code — the "real local communication layer" the testing strategy
requires), so these tests exercise real (de)serialization, tool dispatch,
and error propagation without needing an actual open socket in CI.

Reachability/retry tests live in the sibling file test_mcp_reachability.py
(split out to keep each file under 150 lines).
"""

from __future__ import annotations

import asyncio

from police_thief.infra.mcp_client import MCPPeerClient
from police_thief.infra.mcp_server import MessageMailbox, build_server
from police_thief.infra.protocol import ProtocolMessage, ProtocolResponse, RejectReason


def _always_accept(message: ProtocolMessage) -> ProtocolResponse:
    return ProtocolResponse(accepted=True)


def _always_reject_illegal(message: ProtocolMessage) -> ProtocolResponse:
    return ProtocolResponse(accepted=False, reason=RejectReason.ILLEGAL_MOVE)


def test_successful_commit_round_trip():
    server = build_server("test-peer", _always_accept, MessageMailbox())
    client = MCPPeerClient(server)
    result = asyncio.run(client.send_commit(role="police", step=0, h_commit="abc123"))
    assert result.get("accepted") is True


def test_reveal_rejection_is_returned_not_raised():
    server = build_server("test-peer", _always_reject_illegal, MessageMailbox())
    client = MCPPeerClient(server)
    result = asyncio.run(
        client.send_reveal(role="thief", step=0, move="MOVE:N", hint="", intent="truth")
    )
    assert result.get("accepted") is False
    assert result.get("reason") == RejectReason.ILLEGAL_MOVE.value


def test_duplicate_commit_is_rejected():
    server = build_server("test-peer", _always_accept, MessageMailbox())
    client = MCPPeerClient(server)
    first = asyncio.run(client.send_commit(role="police", step=0, h_commit="abc123"))
    second = asyncio.run(client.send_commit(role="police", step=0, h_commit="abc123"))
    assert first.get("accepted") is True
    assert second.get("accepted") is False
    assert second.get("reason") == RejectReason.DUPLICATE.value


def test_stale_commit_is_rejected():
    server = build_server("test-peer", _always_accept, MessageMailbox())
    client = MCPPeerClient(server)
    asyncio.run(client.send_commit(role="police", step=5, h_commit="abc"))
    stale = asyncio.run(client.send_commit(role="police", step=2, h_commit="abc"))
    assert stale.get("accepted") is False
    assert stale.get("reason") == RejectReason.STALE_TURN.value


def test_invalid_intent_on_reveal_is_rejected():
    server = build_server("test-peer", _always_accept, MessageMailbox())
    client = MCPPeerClient(server)
    result = asyncio.run(
        client.send_reveal(role="police", step=0, move="MOVE:N", hint="", intent="maybe")
    )
    assert result.get("accepted") is False


def test_unknown_role_on_commit_is_rejected():
    server = build_server("test-peer", _always_accept, MessageMailbox())

    async def send_bad_role() -> dict:
        from fastmcp import Client

        async with Client(server) as raw_client:
            result = await raw_client.call_tool(
                "receive_commit", {"role": "villain", "step": 0, "h_commit": "abc"}
            )
            return result.data  # type: ignore[return-value]

    data = asyncio.run(send_bad_role())
    assert data.get("accepted") is False
