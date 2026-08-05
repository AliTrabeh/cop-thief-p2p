"""The own-turn commit/reveal flow for :class:`~police_thief.orchestrator.Orchestrator`
(``produce_commit`` / ``produce_reveal`` / ``confirm_reveal_accepted``) — split out of
``orchestrator.py`` to keep each file under the project's 150-line-per-file limit.
Plain functions taking the orchestrator instance explicitly, matching
``orchestrator_messages.py``'s pattern; see that module's docstring for why.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from police_thief.domain.board import IllegalActionError
from police_thief.domain.crypto import commit as crypto_commit
from police_thief.domain.crypto import hash_state
from police_thief.domain.state_machine import GamePhase
from police_thief.infra.protocol import MessageType, ProtocolMessage, ProtocolResponse
from police_thief.orchestrator_types import (
    LogEntry,
    PendingOwnTurn,
    TechnicalLossError,
    action_to_move_str,
    canonical_board_snapshot,
)
from police_thief.strategy.base import MoveAction, build_belief_view

if TYPE_CHECKING:
    from police_thief.orchestrator import Orchestrator


def produce_commit(orch: Orchestrator) -> ProtocolMessage:
    """Decide an action via the strategy module and commit to it."""
    orch.phase.transition(GamePhase.COMPUTING_MOVE)
    view = build_belief_view(orch.board, orch.opponent_scent, orch.role)
    try:
        action = orch.brain.decide(view)
    except Exception as exc:  # noqa: BLE001 - a buggy pluggable brain (FR-060) must
        # become our own technical loss, never an unhandled crash of the whole peer
        # process (PRD-0286/PRD-0573).
        orch._fail(f"strategy raised {exc.__class__.__name__}: {exc}", disqualified=orch.role)
        raise TechnicalLossError(orch.technical_loss_reason or "strategy error") from exc
    state_hash = hash_state(canonical_board_snapshot(orch.board))
    move_str = action_to_move_str(action)
    intent = orch.brain._decide_intent(view)
    h_commit, nonce = crypto_commit(state=state_hash, move=move_str, intent=intent)
    entry = LogEntry(
        turn_number=orch.turn_number,
        role=orch.role,
        state_hash=state_hash,
        move=move_str,
        intent=intent,
        h_commit=h_commit,
        nonce=nonce,
    )
    orch._pending = PendingOwnTurn(action=action, entry=entry)
    orch.phase.transition(GamePhase.COMMITTING)
    return ProtocolMessage(
        message_type=MessageType.COMMIT,
        game_id=orch.game_id,
        turn_number=orch.turn_number,
        sender_role=orch.role,
        payload={"h_commit": entry.h_commit},
    )


def produce_reveal(orch: Orchestrator, hint: str = "") -> ProtocolMessage:
    """COMMITTING -> AWAITING_REVEAL: reveal move + hint (Nonce still hidden, spec §5.3.2)."""
    if orch._pending is None:
        raise TechnicalLossError("produce_reveal() called before produce_commit()")
    orch.phase.transition(GamePhase.AWAITING_REVEAL)
    entry = orch._pending.entry
    entry.hint = hint
    return ProtocolMessage(
        message_type=MessageType.REVEAL,
        game_id=orch.game_id,
        turn_number=orch.turn_number,
        sender_role=orch.role,
        payload={"move": entry.move, "hint": hint, "intent": entry.intent},
    )


def confirm_reveal_accepted(orch: Orchestrator, response: ProtocolResponse) -> None:
    """AWAITING_REVEAL -> VERIFYING -> WAITING_FOR_OPPONENT: apply our own action
    locally once the opponent confirms the reveal was legal.
    """
    if orch._pending is None:
        raise TechnicalLossError("confirm_reveal_accepted() with no pending turn")
    if not response.accepted:
        orch._fail(f"opponent rejected our reveal: {response.reason}", disqualified=orch.role)
        return
    orch.phase.transition(GamePhase.VERIFYING)
    action = orch._pending.action
    try:
        if isinstance(action, MoveAction):
            orch.board.apply_move(orch.role, action.direction)
        else:
            orch.board.place_barrier(action.coord)
    except IllegalActionError as exc:
        orch._fail(
            f"own action became illegal before it could be applied: {exc}",
            disqualified=orch.role,
        )
        return
    orch.own_log.append(orch._pending.entry)
    orch._pending = None
    orch.turn_number += 1
    if not orch.phase.is_terminal:
        orch.phase.transition(GamePhase.WAITING_FOR_OPPONENT)
