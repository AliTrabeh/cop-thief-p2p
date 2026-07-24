"""Unit tests for orchestrator.py — FR-052/053, TEST-004 (incoming-message
handling half, split out of test_orchestrator.py to keep each file under
150 lines).
"""

from __future__ import annotations

from _orchestrator_helpers import make_orchestrator

from police_thief.domain.models import Coordinate, Role
from police_thief.infra.protocol import MessageType, ProtocolMessage, RejectReason


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
    assert orch.technical_loss_role is Role.THIEF  # the opponent, not us, is disqualified


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
