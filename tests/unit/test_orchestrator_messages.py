"""Unit tests for orchestrator.py — FR-052/053, TEST-004 (incoming-message
handling half, split out of test_orchestrator.py to keep each file under
150 lines).
"""

from __future__ import annotations

from _orchestrator_helpers import make_orchestrator

from police_thief.domain.crypto import commit as crypto_commit
from police_thief.domain.models import Coordinate, Role
from police_thief.infra.protocol import MessageType, ProtocolMessage, RejectReason
from police_thief.orchestrator_types import LogEntry


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


def test_receive_reveal_decays_old_scent_before_depositing_new(game_config):
    # FR-030: τ(t+1) = max(0, (1-ρ)·τ(t) + Δτ). Each reveal must trigger
    # update_turn (decay + deposit), not just deposit, so old positions fade.
    orch = make_orchestrator(game_config, Role.POLICE)

    # Probe cell is at distance 2 from the first deposit site (2,3) and at distance 3
    # from the second deposit site (1,3).  The radius is 2, so the second deposit adds
    # zero falloff to this cell — only decay applies on the second turn.
    probe = Coordinate(row=4, col=3)

    # First reveal: thief moves N from (3,3) to (2,3); probe is exactly at radius edge.
    orch.handle_message(
        ProtocolMessage(
            message_type=MessageType.REVEAL,
            game_id="test-game",
            turn_number=0,
            sender_role=Role.THIEF,
            payload={"move": "MOVE:N"},
        )
    )
    intensity_after_first = orch.opponent_scent.intensity_at(probe)
    assert intensity_after_first > 0

    # Second reveal: thief moves N again from (2,3) to (1,3).
    # probe is outside the radius-2 emission field of (1,3) so no new deposit lands
    # there — the only change must be decay, proving update_turn was called.
    orch.handle_message(
        ProtocolMessage(
            message_type=MessageType.REVEAL,
            game_id="test-game",
            turn_number=1,
            sender_role=Role.THIEF,
            payload={"move": "MOVE:N"},
        )
    )
    intensity_after_second = orch.opponent_scent.intensity_at(probe)
    assert intensity_after_second < intensity_after_first


def test_receive_final_reveal_tampered_hash_causes_technical_loss(game_config):
    # E-19/FR-043: a commitment hash mismatch on Final Reveal is a hard
    # technical disqualification for the opponent, not a soft warning.
    orch = make_orchestrator(game_config, Role.POLICE)
    h_commit, _correct_nonce = crypto_commit("state", "MOVE:N", "truth")
    orch.opponent_log.append(
        LogEntry(turn_number=0, role=Role.THIEF, state_hash="state",
                 move="MOVE:N", intent="truth", h_commit=h_commit)
    )
    response = orch.handle_message(
        ProtocolMessage(
            message_type=MessageType.FINAL_REVEAL,
            game_id="test-game",
            turn_number=0,
            sender_role=Role.THIEF,
            payload={"0": '{"state_hash": "state", "nonce": "wrong-nonce"}'},
        )
    )
    assert not response.accepted
    assert response.reason is RejectReason.INVALID_SIGNATURE
    assert orch.is_over
    assert orch.technical_loss_role is Role.THIEF


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
