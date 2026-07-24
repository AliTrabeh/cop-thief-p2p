"""Unit tests for strategy/qlearning.py — BONUS-001 (optional RL brain)."""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from police_thief.domain.board import BoardState
from police_thief.domain.models import Coordinate, Role
from police_thief.domain.scent import ScentField
from police_thief.strategy.base import BarrierAction, MoveAction, build_belief_view
from police_thief.strategy.qlearning import QLearningPoliceBrain, QLearningThiefBrain
from police_thief.strategy.qlearning_core import state_for


def test_thief_brain_always_returns_a_legal_action(game_config):
    board = BoardState.initial(game_config)
    scent = ScentField(config=game_config)
    scent.deposit(board.cop_position)
    view = build_belief_view(board, scent, Role.THIEF)
    action = QLearningThiefBrain(seed=1).decide(view)
    assert isinstance(action, MoveAction)
    assert action.direction in view.legal_moves


def test_police_brain_always_returns_a_legal_action_or_barrier(game_config):
    board = BoardState.initial(game_config)
    scent = ScentField(config=game_config)
    scent.deposit(board.thief_position)
    view = build_belief_view(board, scent, Role.POLICE)
    action = QLearningPoliceBrain(seed=1).decide(view)
    if isinstance(action, MoveAction):
        assert action.direction in view.legal_moves
    else:
        assert isinstance(action, BarrierAction)
        assert board.can_place_barrier(action.coord)


def test_legality_holds_across_many_random_starting_corners(game_config):
    board = BoardState.initial(game_config)
    scent = ScentField(config=game_config)
    brain = QLearningPoliceBrain(seed=7)
    size = board.config.board_and_agents.grid_size
    for corner in itertools.product((0, size - 1), repeat=2):
        board.cop_position = Coordinate(row=corner[0], col=corner[1])
        view = build_belief_view(board, scent, Role.POLICE)
        action = brain.decide(view)
        assert isinstance(action, MoveAction | BarrierAction)


def test_police_corners_with_barrier_when_thief_believed_adjacent(game_config):
    # Barrier placement reuses the deterministic heuristic rule (documented
    # scope limitation), so this must behave identically to the default brain.
    board = BoardState.initial(game_config)
    board.cop_position = Coordinate(row=3, col=2)
    board.thief_position = Coordinate(row=3, col=3)
    scent = ScentField(config=game_config)
    scent.deposit(board.thief_position)
    view = build_belief_view(board, scent, Role.POLICE)
    action = QLearningPoliceBrain(seed=1).decide(view)
    assert isinstance(action, BarrierAction)
    assert action.coord == board.thief_position


def test_epsilon_zero_is_greedy_over_seeded_q_values(game_config):
    board = BoardState.initial(game_config)
    board.thief_position = Coordinate(row=3, col=3)
    board.cop_position = Coordinate(row=0, col=0)
    scent = ScentField(config=game_config)
    scent.deposit(board.thief_position)
    view = build_belief_view(board, scent, Role.POLICE)

    brain = QLearningPoliceBrain(epsilon=0.0, seed=1)
    state = state_for(view, board.thief_position)
    # Rig the table so "E" (toward the thief, which is south-east of the cop) wins outright.
    brain._q[state] = {"N": -10.0, "S": 0.0, "E": 10.0, "W": -10.0, "STAY": -10.0}
    action = brain.decide(view)
    assert isinstance(action, MoveAction)
    assert action.direction.value == "E"


def test_q_values_update_after_a_second_decision(game_config):
    board = BoardState.initial(game_config)
    # Distance 3 (== _DISTANCE_CAP) at start, 2 after one step east -- picked
    # deliberately so the two turns land in genuinely distinct discretized
    # states (a same-state self-bootstrap would make the arithmetic below
    # depend on the *rigged* Q-value too, which is a real but separate
    # tabular-Q-learning nuance not what this test is isolating).
    board.thief_position = Coordinate(row=0, col=3)
    board.cop_position = Coordinate(row=0, col=0)
    scent = ScentField(config=game_config)
    scent.deposit(board.thief_position)
    brain = QLearningPoliceBrain(epsilon=0.0, seed=1)

    view1 = build_belief_view(board, scent, Role.POLICE)
    state1 = state_for(view1, board.thief_position)
    brain._q[state1] = {"E": 5.0}  # rig the first choice to be deterministic ("E" wins)

    action1 = brain.decide(view1)
    assert isinstance(action1, MoveAction)
    assert action1.direction.value == "E"
    assert brain._q[state1]["E"] == 5.0  # not yet updated (no prior step existed)

    board.cop_position = board.cop_position.translated(action1.direction)  # now one step closer
    view2 = build_belief_view(board, scent, Role.POLICE)
    brain.decide(view2)
    # reward = old_distance - new_distance = 1 (police minimizes); TD target pulls
    # the rigged 5.0 down toward (reward + gamma*best_next) = 1.0, by alpha=0.3:
    # 5.0 + 0.3 * (1.0 + 0.9*0.0 - 5.0) == 3.8
    assert brain._q[state1]["E"] == pytest.approx(3.8)


def test_save_and_load_round_trips_the_q_table(tmp_path: Path, game_config):
    board = BoardState.initial(game_config)
    scent = ScentField(config=game_config)
    scent.deposit(board.thief_position)
    brain = QLearningPoliceBrain(epsilon=0.0, seed=1)

    view1 = build_belief_view(board, scent, Role.POLICE)
    action1 = brain.decide(view1)
    assert isinstance(action1, MoveAction)
    board.cop_position = board.cop_position.translated(action1.direction)
    brain.decide(build_belief_view(board, scent, Role.POLICE))
    assert brain._q  # something was learned

    path = tmp_path / "q.json"
    brain.save(path)

    reloaded = QLearningPoliceBrain(epsilon=0.0, seed=2, q_table_path=path)
    assert reloaded._q == brain._q


def test_thief_state_discretization_uses_signed_deltas_and_capped_distance(game_config):
    board = BoardState.initial(game_config)
    board.thief_position = Coordinate(row=0, col=0)
    target = Coordinate(row=5, col=5)
    scent = ScentField(config=game_config)
    view = build_belief_view(board, scent, Role.THIEF)
    state = state_for(view, target)
    assert state[0] == 1  # target is east (higher col)
    assert state[1] == 1  # target is south (higher row)
    assert state[2] == 3  # capped at _DISTANCE_CAP even though true distance is 10
    assert state[3] is False  # thief can never place a barrier
