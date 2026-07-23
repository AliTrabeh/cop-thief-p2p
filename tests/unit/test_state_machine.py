"""Unit tests for domain/state_machine.py — TEST-004, FR-052."""

from __future__ import annotations

import pytest

from police_thief.domain.state_machine import GamePhase, GamePhaseMachine, IllegalTransitionError


def test_initial_state_is_waiting_for_opponent():
    m = GamePhaseMachine()
    assert m.state is GamePhase.WAITING_FOR_OPPONENT
    assert not m.is_terminal


def test_full_happy_path_cycle_back_to_waiting():
    m = GamePhaseMachine()
    m.transition(GamePhase.COMPUTING_MOVE)
    m.transition(GamePhase.COMMITTING)
    m.transition(GamePhase.AWAITING_REVEAL)
    m.transition(GamePhase.VERIFYING)
    m.transition(GamePhase.WAITING_FOR_OPPONENT)
    assert m.state is GamePhase.WAITING_FOR_OPPONENT


@pytest.mark.parametrize(
    "from_state",
    [GamePhase.COMPUTING_MOVE, GamePhase.AWAITING_REVEAL, GamePhase.VERIFYING],
)
def test_technical_loss_reachable_from_three_states(from_state):
    m = GamePhaseMachine()
    m.transition(GamePhase.COMPUTING_MOVE)
    if from_state is GamePhase.AWAITING_REVEAL or from_state is GamePhase.VERIFYING:
        m.transition(GamePhase.COMMITTING)
        m.transition(GamePhase.AWAITING_REVEAL)
    if from_state is GamePhase.VERIFYING:
        m.transition(GamePhase.VERIFYING)
    assert m.state is from_state
    m.transition(GamePhase.TECHNICAL_LOSS)
    assert m.state is GamePhase.TECHNICAL_LOSS
    assert m.is_terminal


def test_technical_loss_is_terminal_no_outgoing_transitions():
    m = GamePhaseMachine()
    m.transition(GamePhase.COMPUTING_MOVE)
    m.transition(GamePhase.TECHNICAL_LOSS)
    for target in GamePhase:
        with pytest.raises(IllegalTransitionError):
            m.transition(target)
    assert m.state is GamePhase.TECHNICAL_LOSS


@pytest.mark.parametrize(
    ("start", "illegal_target"),
    [
        (GamePhase.WAITING_FOR_OPPONENT, GamePhase.COMMITTING),
        (GamePhase.WAITING_FOR_OPPONENT, GamePhase.VERIFYING),
        (GamePhase.COMPUTING_MOVE, GamePhase.WAITING_FOR_OPPONENT),
        (GamePhase.COMMITTING, GamePhase.TECHNICAL_LOSS),
        (GamePhase.COMMITTING, GamePhase.COMMITTING),
    ],
)
def test_illegal_transitions_are_rejected_and_state_unchanged(start, illegal_target):
    m = GamePhaseMachine()
    # drive to `start`
    path = {
        GamePhase.WAITING_FOR_OPPONENT: [],
        GamePhase.COMPUTING_MOVE: [GamePhase.COMPUTING_MOVE],
        GamePhase.COMMITTING: [GamePhase.COMPUTING_MOVE, GamePhase.COMMITTING],
    }[start]
    for step in path:
        m.transition(step)
    assert m.state is start
    with pytest.raises(IllegalTransitionError):
        m.transition(illegal_target)
    assert m.state is start  # rejected transition must not change state
