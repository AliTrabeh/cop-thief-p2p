"""FastMCP tool server: exposes dedicated per-step tools for the commit-reveal
protocol (spec Section 2.3.2, Figure 6).

Each protocol step has its own named tool, matching the spec's explicit design:
  receive_step0          — pre-game hardware/software declaration (§5.5)
  receive_commit         — Step 1: sealed commitment, H_commit only (§5.3.1)
  receive_ack            — Step 2: acknowledgment that commit is locked in (§5.3.2)
  receive_reveal         — Step 3: move + verbal hint, Nonce still hidden (§5.3.2)
  receive_final_audit    — Step 4: all Nonces for end-of-game audit (§5.4)
  receive_capture_claim  — capture claim from cop side (§3.5)

The server is split into two concerns:
  - Message routing / sequencing (this file, networking layer — no game rules)
  - Game logic (orchestrator — called via `handler` callback for commit/reveal/audit)

`receive_ack`, `receive_step0`, and `receive_capture_claim` only queue into
`MessageMailbox`; the peer runtime drains those queues when it needs them.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field

from fastmcp import FastMCP

from police_thief.domain.models import Role
from police_thief.infra.protocol import (
    MessageType,
    ProtocolMessage,
    ProtocolResponse,
    RejectReason,
)

MessageHandler = Callable[[ProtocolMessage], ProtocolResponse]

_LEGAL_ROLES = {"police", "thief"}


@dataclass
class SequenceTracker:
    """Protocol-level bookkeeping: rejects stale or duplicate messages.
    Tracked per MessageType so COMMIT and REVEAL sharing the same turn_number
    don't incorrectly deduplicate each other.
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


@dataclass
class MessageMailbox:
    """Async-safe per-message-kind inboxes (spec Figure 6).

    acks           — ACKs received by THIS peer (opponent called our receive_ack).
                     The active player awaits this queue after sending a commit.
    pending_acks   — Notifies the passive player's runtime that it must send an
                     ACK back to the active player's receive_ack tool.
    step0s         — Received Step-0 hardware/software declarations (§5.5).
    capture_claims — Received capture claims from the cop side (§3.5).
    """

    acks: asyncio.Queue = field(default_factory=asyncio.Queue)
    pending_acks: asyncio.Queue = field(default_factory=asyncio.Queue)
    step0s: asyncio.Queue = field(default_factory=asyncio.Queue)
    capture_claims: asyncio.Queue = field(default_factory=asyncio.Queue)


def build_server(name: str, handler: MessageHandler, mailbox: MessageMailbox) -> FastMCP:
    """Build a FastMCP server with dedicated tools per protocol step (spec §2.3.2).

    `handler` is the Orchestrator's dispatch function — tools that carry game
    state (commit, reveal, final_audit) delegate to it; tools that are pure
    transport signals (ack, step0, capture_claim) only queue into `mailbox`.
    """
    mcp = FastMCP(name)
    tracker = SequenceTracker()

    @mcp.tool
    async def receive_step0(role: str, declaration: dict, signature: str) -> dict:
        """Receive the opponent's pre-game Step-0 hardware/software declaration (§5.5)."""
        if role not in _LEGAL_ROLES:
            return {"accepted": False, "error": f"unknown role {role!r}"}
        await mailbox.step0s.put(
            {"role": role, "declaration": declaration, "signature": signature}
        )
        return {"accepted": True}

    @mcp.tool
    async def receive_commit(role: str, step: int, h_commit: str) -> dict:
        """Receive Step 1 sealed commitment — content unknown until Reveal (§5.3.1).

        On acceptance, queues into `mailbox.pending_acks` so the passive player's
        runtime knows to call the active player's `receive_ack` tool separately.
        """
        if role not in _LEGAL_ROLES:
            return {"accepted": False, "error": f"unknown role {role!r}"}
        sequence_issue = tracker.check(MessageType.COMMIT, step)
        if sequence_issue is not None:
            return ProtocolResponse(accepted=False, reason=sequence_issue).model_dump(mode="json")
        msg = ProtocolMessage(
            message_type=MessageType.COMMIT,
            game_id="",
            turn_number=step,
            sender_role=Role(role),
            payload={"h_commit": h_commit},
        )
        response = handler(msg)
        if response.accepted:
            tracker.record(MessageType.COMMIT, step)
            await mailbox.pending_acks.put({"role": role, "step": step})
        return {"accepted": response.accepted}

    @mcp.tool
    async def receive_ack(role: str, step: int) -> dict:
        """Acknowledge the opponent's commitment is locked in (§5.3.2 Step 2).

        Queued into `mailbox.acks`; the active player's runtime awaits this queue
        after sending a commit, before sending the reveal.
        """
        if role not in _LEGAL_ROLES:
            return {"accepted": False, "error": f"unknown role {role!r}"}
        await mailbox.acks.put({"role": role, "step": step})
        return {"accepted": True}

    @mcp.tool
    async def receive_reveal(
        role: str, step: int, move: str, hint: str, intent: str
    ) -> dict:
        """Receive Step 3 reveal: move + verbal hint, Nonce still hidden (§5.3.2).

        `intent` must be 'truth' or 'lie' — the bluff flag committed to in Step 1.
        Move legality is validated by the orchestrator handler immediately so the
        active player gets synchronous feedback.
        """
        if role not in _LEGAL_ROLES:
            return {"accepted": False, "error": f"unknown role {role!r}"}
        if intent not in ("truth", "lie"):
            return {"accepted": False, "error": f"unknown intent {intent!r}"}
        sequence_issue = tracker.check(MessageType.REVEAL, step)
        if sequence_issue is not None:
            return ProtocolResponse(accepted=False, reason=sequence_issue).model_dump(mode="json")
        msg = ProtocolMessage(
            message_type=MessageType.REVEAL,
            game_id="",
            turn_number=step,
            sender_role=Role(role),
            payload={"move": move, "hint": hint, "intent": intent},
        )
        response = handler(msg)
        if response.accepted:
            tracker.record(MessageType.REVEAL, step)
        return response.model_dump(mode="json")

    @mcp.tool
    async def receive_final_audit(role: str, nonces: dict[str, str]) -> dict:
        """Receive Step 4: all Nonces for end-of-game mutual audit (§5.4)."""
        if role not in _LEGAL_ROLES:
            return {"accepted": False, "error": f"unknown role {role!r}"}
        msg = ProtocolMessage(
            message_type=MessageType.FINAL_REVEAL,
            game_id="",
            turn_number=0,
            sender_role=Role(role),
            payload=nonces,
        )
        response = handler(msg)
        return response.model_dump(mode="json")

    @mcp.tool
    async def receive_capture_claim(role: str, claimed: bool) -> dict:
        """Receive a capture claim from the cop; the thief must respond truthfully (§3.5)."""
        if role not in _LEGAL_ROLES:
            return {"accepted": False, "error": f"unknown role {role!r}"}
        await mailbox.capture_claims.put({"role": role, "claimed": claimed})
        return {"accepted": True}

    return mcp
