"""Unit tests for orchestrator.py — FR-052/053, TEST-004 (own-turn flow half;
incoming-message tests live in the sibling file test_orchestrator_messages.py,
split out to keep each file under 150 lines).
"""

from __future__ import annotations

from _orchestrator_helpers import CrashingBrain, make_orchestrator

from police_thief.domain.board import BoardState
from police_thief.domain.models import Role
from police_thief.domain.state_machine import GamePhase
from police_thief.infra.protocol import MessageType, ProtocolResponse, RejectReason
from police_thief.orchestrator import Orchestrator, TechnicalLossError


def test_produce_commit_transitions_and_locks_an_action(game_config):
    orch = make_orchestrator(game_config, Role.POLICE)
    message = orch.produce_commit()
    assert orch.phase.state is GamePhase.COMMITTING
    assert message.message_type is MessageType.COMMIT
    assert message.turn_number == 0
    assert "h_commit" in message.payload


def test_produce_reveal_transitions_to_awaiting_reveal(game_config):
    orch = make_orchestrator(game_config, Role.POLICE)
    orch.produce_commit()
    message = orch.produce_reveal()
    assert orch.phase.state is GamePhase.AWAITING_REVEAL
    assert message.message_type is MessageType.REVEAL
    assert message.payload["move"].startswith(("MOVE:", "BARRIER:"))


def test_confirm_reveal_accepted_applies_action_and_returns_to_waiting(game_config):
    orch = make_orchestrator(game_config, Role.POLICE)
    orch.produce_commit()
    orch.produce_reveal()
    orch.confirm_reveal_accepted(ProtocolResponse(accepted=True))
    assert orch.phase.state is GamePhase.WAITING_FOR_OPPONENT
    assert len(orch.own_log) == 1
    assert orch.turn_number == 1
    # With zero scent info yet, the default heuristic's belief map is
    # uniform and argmax degenerately ties on (0,0) -- the cop's own start
    # cell -- so `moves_made` incrementing (a STAY was legally applied) is
    # the real signal the turn was actually processed, not necessarily a
    # position change.
    assert orch.board.moves_made == 1


def test_confirm_reveal_rejected_causes_technical_loss(game_config):
    orch = make_orchestrator(game_config, Role.POLICE)
    orch.produce_commit()
    orch.produce_reveal()
    orch.confirm_reveal_accepted(ProtocolResponse(accepted=False, reason=RejectReason.ILLEGAL_MOVE))
    assert orch.phase.state is GamePhase.TECHNICAL_LOSS
    assert orch.technical_loss_reason is not None
    assert orch.technical_loss_role is Role.POLICE  # we (police) are the disqualified side here
    assert orch.is_over


def test_produce_commit_with_crashing_brain_becomes_own_technical_loss(game_config):
    board = BoardState.initial(game_config)
    orch = Orchestrator(
        role=Role.POLICE,
        game_id="test-game",
        config=game_config,
        board=board,
        brain=CrashingBrain(),
    )
    try:
        orch.produce_commit()
    except TechnicalLossError:
        pass
    else:
        raise AssertionError("expected TechnicalLossError from a crashing brain")
    assert orch.is_over
    assert orch.phase.state is GamePhase.TECHNICAL_LOSS
    assert orch.technical_loss_role is Role.POLICE
    assert "RuntimeError" in (orch.technical_loss_reason or "")


def test_repeated_full_turn_cycle_advances_turn_number(game_config):
    orch = make_orchestrator(game_config, Role.POLICE)
    for expected_turn in range(3):
        assert orch.turn_number == expected_turn
        orch.produce_commit()
        orch.produce_reveal()
        orch.confirm_reveal_accepted(ProtocolResponse(accepted=True))
    assert orch.turn_number == 3
    assert len(orch.own_log) == 3


def test_reject_own_commit_causes_technical_loss(game_config):
    orch = make_orchestrator(game_config, Role.POLICE)
    orch.produce_commit()
    orch.reject_own_commit(ProtocolResponse(accepted=False, reason=RejectReason.STALE_TURN))
    assert orch.is_over
    assert orch.technical_loss_role is Role.POLICE
