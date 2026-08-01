"""Incoming-message handling for :class:`~police_thief.orchestrator.Orchestrator`
(dispatch, the two REVEAL/COMMIT receivers, end-of-game FINAL_REVEAL audit, and log
export) — split out of ``orchestrator.py`` to keep each file under the project's
150-line-per-file limit. These are plain functions taking the orchestrator instance
explicitly (not methods) purely to avoid a circular import at runtime; the type is
only needed for annotations, so it's imported under ``TYPE_CHECKING``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from police_thief.domain.board import IllegalActionError
from police_thief.domain.crypto import verify as crypto_verify
from police_thief.infra.protocol import MessageType, ProtocolMessage, ProtocolResponse, RejectReason
from police_thief.orchestrator_types import (
    LogEntry,
    barrier_coord_from_move_str,
    direction_from_move_str,
    opponent_of,
)

if TYPE_CHECKING:
    from police_thief.orchestrator import Orchestrator


def handle_message(orch: Orchestrator, message: ProtocolMessage) -> ProtocolResponse:
    """Dispatch table used by the FastMCP server handler (Part 8)."""
    if message.message_type is MessageType.COMMIT:
        return receive_commit(orch, message)
    if message.message_type is MessageType.REVEAL:
        return receive_reveal(orch, message)
    if message.message_type is MessageType.FINAL_REVEAL:
        return receive_final_reveal(orch, message)
    return ProtocolResponse(accepted=False, reason=RejectReason.MALFORMED)


def produce_final_reveal(orch: Orchestrator) -> ProtocolMessage:
    """End-of-game: reveal every nonce this side ever committed (§5.3.2 step 4), so
    the opponent (and the standalone Replay Viewer, Part 13) can independently
    recompute and verify every commitment hash.
    """
    payload = {
        str(entry.turn_number): json.dumps({"state_hash": entry.state_hash, "nonce": entry.nonce})
        for entry in orch.own_log
    }
    return ProtocolMessage(
        message_type=MessageType.FINAL_REVEAL,
        game_id=orch.game_id,
        turn_number=orch.turn_number,
        sender_role=orch.role,
        payload=payload,
    )


def receive_final_reveal(orch: Orchestrator, message: ProtocolMessage) -> ProtocolResponse:
    """Fill in the opponent's ``state_hash``/``nonce`` for every turn we already
    recorded, then verify every commitment hash (FR-043/E-19: mismatch = hard
    technical disqualification, §5.4 mutual audit).
    """
    opponent_role = opponent_of(orch.role)
    for entry in orch.opponent_log:
        key = str(entry.turn_number)
        if key not in message.payload:
            continue
        data = json.loads(message.payload[key])
        entry.state_hash = data["state_hash"]
        entry.nonce = data["nonce"]
    for entry in orch.opponent_log:
        if not entry.nonce or not entry.h_commit:
            continue
        if not crypto_verify(entry.state_hash, entry.move, entry.intent, entry.nonce,
                              entry.h_commit):
            orch._fail(
                f"commitment hash mismatch on turn {entry.turn_number}",
                disqualified=opponent_role,
            )
            return ProtocolResponse(accepted=False, reason=RejectReason.INVALID_SIGNATURE)
    return ProtocolResponse(accepted=True)


def export_log(orch: Orchestrator) -> list[dict[str, object]]:
    """Merge our own and the opponent's log entries, sorted by turn, in the shape
    the Replay Viewer (Part 13) expects.
    """
    combined = [*orch.own_log, *orch.opponent_log]
    combined.sort(key=lambda e: (e.turn_number, e.role.value))
    return [
        {
            "turn_number": e.turn_number,
            "role": e.role.value,
            "state_hash": e.state_hash,
            "move": e.move,
            "intent": e.intent,
            "h_commit": e.h_commit,
            "nonce": e.nonce,
        }
        for e in combined
    ]


def receive_commit(orch: Orchestrator, message: ProtocolMessage) -> ProtocolResponse:
    """Record the opponent's commitment hash for the end-of-game audit; no board
    mutation happens on a bare commit (docs/protocol.md §3).
    """
    orch._pending_opponent_commit = message.payload.get("h_commit", "")
    return ProtocolResponse(accepted=True)


def receive_reveal(orch: Orchestrator, message: ProtocolMessage) -> ProtocolResponse:
    """Apply the opponent's revealed move to our mirror of their position, checking
    legality immediately. The cryptographic proof that this reveal matches the
    earlier commit is deferred to the end-of-game audit (§5.4) since the nonce
    isn't sent yet.
    """
    opponent_role = opponent_of(orch.role)
    move_str = message.payload.get("move", "")
    try:
        if move_str.startswith("MOVE:"):
            orch.board.apply_move(opponent_role, direction_from_move_str(move_str))
        elif move_str.startswith("BARRIER:"):
            orch.board.place_barrier(barrier_coord_from_move_str(move_str))
        else:
            return ProtocolResponse(accepted=False, reason=RejectReason.MALFORMED)
    except IllegalActionError:
        orch._fail("opponent's revealed move was illegal", disqualified=opponent_role)
        return ProtocolResponse(accepted=False, reason=RejectReason.ILLEGAL_MOVE)

    orch.opponent_log.append(
        LogEntry(
            turn_number=message.turn_number,
            role=opponent_role,
            state_hash="",  # unknown until FINAL_REVEAL
            move=move_str,
            intent="truth",
            h_commit=orch._pending_opponent_commit,
        )
    )
    orch.opponent_scent.update_turn(orch.board.position_of(opponent_role))
    return ProtocolResponse(accepted=True)
