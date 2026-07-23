"""Wire message schema for the FastMCP transport (PROTO-001..004, docs/protocol.md).

The networking layer never contains game rules (architecture.md §3): this
module only defines *shapes*; ``orchestrator.py`` (Part 9) decides what a
message means.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from police_thief.domain.models import Role


class MessageType(StrEnum):
    """The 4-phase commit-reveal sequence (docs/protocol.md §3)."""

    COMMIT = "COMMIT"
    ACK = "ACK"
    REVEAL = "REVEAL"
    FINAL_REVEAL = "FINAL_REVEAL"


class RejectReason(StrEnum):
    INVALID_SIGNATURE = "invalid_signature"
    ILLEGAL_MOVE = "illegal_move"
    STALE_TURN = "stale_turn"
    DUPLICATE = "duplicate"
    MALFORMED = "malformed"


class ProtocolMessage(BaseModel):
    """A single message in the commit-reveal sequence."""

    schema_version: str = "1.0"
    message_type: MessageType
    game_id: str
    turn_number: int
    sender_role: Role
    payload: dict[str, str]


class ProtocolResponse(BaseModel):
    accepted: bool
    reason: RejectReason | None = None
