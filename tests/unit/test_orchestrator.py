"""Unit tests for orchestrator.py — FR-052/053, TEST-004."""

from __future__ import annotations

from police_thief.domain.board import BoardState
from police_thief.domain.models import Coordinate, Role
from police_thief.domain.state_machine import GamePhase
from police_thief.infra.protocol import MessageType, ProtocolMessage, ProtocolResponse, RejectReason
from police_thief.orchestrator import Orchestrator
from police_thief.strategy.heuristic import HeuristicPoliceBrain, HeuristicThiefBrain


def make_orchestrator(game_config, role: Role) -> Orchestrator:
    board = BoardState.initial(game_config)
    brain = HeuristicPoliceBrain() if role is Role.POLICE else HeuristicThiefBrain()
    return Orchestrator(
        role=role, game_id="test-game", config=game_config, board=board, brain=brain
    )


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
    assert orch.is_over


def test_receive_commit_does_not_mutate_the_board(game_config):
    orch = make_orchestrator(game_config, Role.POLICE)
    before = (orch.board.cop_position, orch.board.thief_position)
    response = orch.handle_message(
        ProtocolMessage(
            message_type=MessageType.COMMIT,
            game_id="test-game",
            turn_number=0,
            sender_role=Role.THIEF,
            payload={"h_commit": "deadbeef"},
        )
    )
    assert response.accepted
    assert (orch.board.cop_position, orch.board.thief_position) == before
    assert orch._pending_opponent_commit == "deadbeef"


def test_receive_reveal_applies_opponent_move_and_updates_belief(game_config):
    orch = make_orchestrator(game_config, Role.POLICE)  # our role is police
    response = orch.handle_message(
        ProtocolMessage(
            message_type=MessageType.REVEAL,
            game_id="test-game",
            turn_number=0,
            sender_role=Role.THIEF,
            payload={"move": "MOVE:N"},
        )
    )
    assert response.accepted
    assert orch.board.thief_position == Coordinate(row=2, col=3)  # started at (3,3), moved N
    assert len(orch.opponent_log) == 1
    assert orch.opponent_scent.intensity_at(Coordinate(row=2, col=3)) > 0


def test_receive_reveal_with_illegal_move_causes_technical_loss(game_config):
    orch = make_orchestrator(game_config, Role.POLICE)
    # Thief starts at (3,3); moving WEST repeatedly off the board is illegal
    # once out of bounds is attempted directly via a crafted out-of-range move.
    orch.board.thief_position = Coordinate(row=0, col=0)
    response = orch.handle_message(
        ProtocolMessage(
            message_type=MessageType.REVEAL,
            game_id="test-game",
            turn_number=0,
            sender_role=Role.THIEF,
            payload={"move": "MOVE:N"},  # off the top edge from row 0
        )
    )
    assert not response.accepted
    assert response.reason is RejectReason.ILLEGAL_MOVE
    assert orch.is_over


def test_receive_reveal_malformed_move_is_rejected(game_config):
    orch = make_orchestrator(game_config, Role.POLICE)
    response = orch.handle_message(
        ProtocolMessage(
            message_type=MessageType.REVEAL,
            game_id="test-game",
            turn_number=0,
            sender_role=Role.THIEF,
            payload={"move": "NOT-A-VALID-ACTION"},
        )
    )
    assert not response.accepted
    assert response.reason is RejectReason.MALFORMED
    assert not orch.is_over  # a malformed message doesn't itself disqualify anyone


def test_repeated_full_turn_cycle_advances_turn_number(game_config):
    orch = make_orchestrator(game_config, Role.POLICE)
    for expected_turn in range(3):
        assert orch.turn_number == expected_turn
        orch.produce_commit()
        orch.produce_reveal()
        orch.confirm_reveal_accepted(ProtocolResponse(accepted=True))
    assert orch.turn_number == 3
    assert len(orch.own_log) == 3
