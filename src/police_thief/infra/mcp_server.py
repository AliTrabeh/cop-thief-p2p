"""FastMCP tool server: exposes this peer's move-submission endpoint
(FR-050/FR-051, architecture.md §3 — the networking layer never contains
game rules; it only parses, sequences, and delegates to a handler).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from fastmcp import FastMCP
from pydantic import ValidationError

from police_thief.infra.protocol import (
    MessageType,
    ProtocolMessage,
    ProtocolResponse,
    RejectReason,
)

MessageHandler = Callable[[ProtocolMessage], ProtocolResponse]


@dataclass
class SequenceTracker:
    """Protocol-level (not game-rule) bookkeeping: rejects a turn number
    lower than the next expected one (stale) or already processed
    (duplicate, handled idempotently rather than as an error).

    Tracked per :class:`MessageType`: COMMIT and REVEAL legitimately share
    the same ``turn_number`` (both belong to the same logical turn, sent a
    few steps apart per docs/protocol.md §3) — deduplicating only by
    ``turn_number`` would make a REVEAL look like a duplicate of its own
    turn's earlier COMMIT.
    """

    expected_turn: dict[MessageType, int] = field(default_factory=dict)
    _seen: set[tuple[MessageType, int]] = field(default_factory=set)

    def check(self, message_type: MessageType, turn_number: int) -> RejectReason | None:
        if (message_type, turn_number) in self._seen:
            return RejectReason.DUPLICATE
        if turn_number < self.expected_turn.get(message_type, 0):
            return RejectReason.STALE_TURN
        return None

    def record(self, message_type: MessageType, turn_number: int) -> None:
        self._seen.add((message_type, turn_number))
        self.expected_turn[message_type] = max(
            self.expected_turn.get(message_type, 0), turn_number + 1
        )


def build_server(name: str, handler: MessageHandler, max_payload_fields: int = 32) -> FastMCP:
    """Build a FastMCP server exposing a single ``submit_message`` tool.

    ``handler`` is the Orchestrator's dispatch function (Part 9) — this
    function only handles MCP wiring, schema validation, and duplicate/stale
    sequencing; it never evaluates game rules itself (NFR-006's DoS guard:
    reject oversized payloads before they ever reach the handler).
    """
    mcp = FastMCP(name)
    tracker = SequenceTracker()

    @mcp.tool
    def submit_message(message: dict[str, object]) -> dict[str, object]:
        """Receive a single commit-reveal protocol message from the opponent."""
        payload = message.get("payload") or {}
        if not isinstance(payload, dict) or len(payload) > max_payload_fields:
            return ProtocolResponse(accepted=False, reason=RejectReason.MALFORMED).model_dump(
                mode="json"
            )
        try:
            parsed = ProtocolMessage.model_validate(message)
        except ValidationError:
            return ProtocolResponse(accepted=False, reason=RejectReason.MALFORMED).model_dump(
                mode="json"
            )

        sequence_issue = tracker.check(parsed.message_type, parsed.turn_number)
        if sequence_issue is not None:
            # A duplicate of an already-accepted message is not an error to
            # surface loudly, but it is never re-applied (idempotency).
            return ProtocolResponse(accepted=False, reason=sequence_issue).model_dump(mode="json")

        response = handler(parsed)
        if response.accepted:
            tracker.record(parsed.message_type, parsed.turn_number)
        return response.model_dump(mode="json")

    return mcp
