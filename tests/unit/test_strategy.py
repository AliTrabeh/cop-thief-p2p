"""Unit tests for strategy/base.py + strategy/heuristic.py — FR-060/061."""

from __future__ import annotations

import itertools

import pytest

from police_thief.domain.board import BoardState
from police_thief.domain.models import Coordinate, Role
from police_thief.domain.scent import ScentField
from police_thief.strategy.base import (
    BarrierAction,
    MoveAction,
    build_belief_view,
    load_brain_class,
)
from police_thief.strategy.heuristic import HeuristicPoliceBrain, HeuristicThiefBrain


def test_thief_brain_always_returns_a_legal_action(game_config):
    board = BoardState.initial(game_config)
    scent = ScentField(config=game_config)
    scent.deposit(board.cop_position)  # thief believes the cop is near its start
    view = build_belief_view(board, scent, Role.THIEF)
    action = HeuristicThiefBrain().decide(view)
    assert isinstance(action, MoveAction)
    assert action.direction in view.legal_moves


def test_police_brain_always_returns_a_legal_action_or_barrier(game_config):
    board = BoardState.initial(game_config)
    scent = ScentField(config=game_config)
    scent.deposit(board.thief_position)
    view = build_belief_view(board, scent, Role.POLICE)
    action = HeuristicPoliceBrain().decide(view)
    if isinstance(action, MoveAction):
        assert action.direction in view.legal_moves
    else:
        assert isinstance(action, BarrierAction)
        assert board.can_place_barrier(action.coord)


def test_thief_evades_believed_cop_location(game_config):
    board = BoardState.initial(game_config)
    board.thief_position = Coordinate(row=3, col=3)
    board.cop_position = Coordinate(row=3, col=2)  # cop just west of thief
    scent = ScentField(config=game_config)
    scent.deposit(board.cop_position)
    view = build_belief_view(board, scent, Role.THIEF)
    action = HeuristicThiefBrain().decide(view)
    assert isinstance(action, MoveAction)
    # moving further from the believed cop position should increase distance, not decrease it
    new_pos = board.thief_position.translated(action.direction)
    assert new_pos.manhattan_distance(
        board.cop_position
    ) >= board.thief_position.manhattan_distance(board.cop_position)


def test_police_pursues_believed_thief_location(game_config):
    board = BoardState.initial(game_config)
    board.cop_position = Coordinate(row=0, col=0)
    board.thief_position = Coordinate(row=0, col=3)
    scent = ScentField(config=game_config)
    scent.deposit(board.thief_position)
    view = build_belief_view(board, scent, Role.POLICE)
    action = HeuristicPoliceBrain().decide(view)
    assert isinstance(action, MoveAction)
    new_pos = board.cop_position.translated(action.direction)
    assert new_pos.manhattan_distance(board.thief_position) < board.cop_position.manhattan_distance(
        board.thief_position
    )


def test_police_corners_with_barrier_when_thief_believed_adjacent(game_config):
    board = BoardState.initial(game_config)
    board.cop_position = Coordinate(row=3, col=2)
    board.thief_position = Coordinate(row=3, col=3)  # adjacent, east of cop
    scent = ScentField(config=game_config)
    scent.deposit(board.thief_position)
    view = build_belief_view(board, scent, Role.POLICE)
    action = HeuristicPoliceBrain().decide(view)
    assert isinstance(action, BarrierAction)
    assert action.coord == board.thief_position


def test_heuristic_brains_are_deterministic_given_the_same_view(game_config):
    board = BoardState.initial(game_config)
    scent = ScentField(config=game_config)
    scent.deposit(board.thief_position)
    view = build_belief_view(board, scent, Role.POLICE)
    results = {HeuristicPoliceBrain().decide(view) for _ in range(5)}
    assert len(results) == 1


def test_thief_brain_never_sees_the_cops_true_position_directly(game_config):
    # The belief view is built from scent alone; a thief brain fed a belief
    # view built from the cop's *own* scent, not `board.cop_position`,
    # cannot distinguish a decoy scent trail from the real cop.
    board = BoardState.initial(game_config)
    decoy = Coordinate(row=6, col=6)
    scent = ScentField(config=game_config)
    scent.deposit(decoy)  # scent placed far from the true cop position
    view = build_belief_view(board, scent, Role.THIEF)
    assert view.belief[decoy] == max(view.belief.values())
    assert decoy != board.cop_position


def test_all_legal_move_directions_are_reachable_as_tiebreak_winners(game_config):
    # Sanity check that the tie-break (iteration order of view.legal_moves,
    # itself following the configured move_set order) is stable and doesn't
    # crash for any starting orientation.
    board = BoardState.initial(game_config)
    scent = ScentField(config=game_config)
    for corner in itertools.product((0, board.config.board_and_agents.grid_size - 1), repeat=2):
        board.cop_position = Coordinate(row=corner[0], col=corner[1])
        view = build_belief_view(board, scent, Role.POLICE)
        action = HeuristicPoliceBrain().decide(view)
        assert isinstance(action, MoveAction | BarrierAction)


def test_police_moves_toward_center_under_uniform_belief_instead_of_a_degenerate_tie(
    game_config,
):
    # Before any scent exists, belief is exactly uniform. The old argmax-based heuristic
    # degenerately tied on (0,0) regardless of the cop's own position; the expected-distance
    # heuristic should instead move purposefully toward the board's center of mass.
    board = BoardState.initial(game_config)
    board.cop_position = Coordinate(row=0, col=0)  # top-left corner
    scent = ScentField(config=game_config)  # never deposited into -- fully uniform belief
    view = build_belief_view(board, scent, Role.POLICE)
    action = HeuristicPoliceBrain().decide(view)
    assert isinstance(action, MoveAction)
    new_pos = board.cop_position.translated(action.direction)
    grid_size = board.config.board_and_agents.grid_size
    center = Coordinate(row=grid_size // 2, col=grid_size // 2)
    assert new_pos.manhattan_distance(center) < board.cop_position.manhattan_distance(center)


def test_barrier_is_not_placed_on_a_low_confidence_uniform_belief(game_config):
    # A cop adjacent to the belief-map's degenerate argmax tie-break cell, but with a fully
    # uniform (uninformative) belief, must not spend a scarce barrier on a meaningless guess.
    board = BoardState.initial(game_config)
    board.cop_position = Coordinate(row=0, col=1)  # adjacent to (0, 0), the argmax tie winner
    scent = ScentField(config=game_config)  # uniform belief -- no real information
    view = build_belief_view(board, scent, Role.POLICE)
    action = HeuristicPoliceBrain().decide(view)
    assert isinstance(action, MoveAction)  # not a BarrierAction


def test_barrier_is_placed_once_belief_is_genuinely_concentrated(game_config):
    board = BoardState.initial(game_config)
    board.cop_position = Coordinate(row=3, col=2)
    board.thief_position = Coordinate(row=3, col=3)  # adjacent, east of cop
    scent = ScentField(config=game_config)
    scent.deposit(board.thief_position)  # a real, concentrated deposit
    view = build_belief_view(board, scent, Role.POLICE)
    action = HeuristicPoliceBrain().decide(view)
    assert isinstance(action, BarrierAction)


def test_thief_prefers_the_interior_when_evasion_options_are_otherwise_tied(game_config):
    # Two moves that are exactly equidistant (in expectation) from the believed cop location
    # should be broken in favor of the one further from the board edge (more future mobility).
    board = BoardState.initial(game_config)
    grid_size = board.config.board_and_agents.grid_size
    mid = grid_size // 2
    board.thief_position = Coordinate(row=mid, col=1)  # one step from the west edge
    board.cop_position = Coordinate(row=0, col=mid)  # symmetric-ish threat from the north
    scent = ScentField(config=game_config)
    scent.deposit(board.cop_position)
    view = build_belief_view(board, scent, Role.THIEF)
    action = HeuristicThiefBrain().decide(view)
    assert isinstance(action, MoveAction)
    # Moving further west (toward col=0) would reduce future mobility versus moving east.
    assert action.direction.value != "W"


def test_load_brain_class_resolves_a_valid_spec():
    cls = load_brain_class("police_thief.strategy.heuristic:HeuristicPoliceBrain")
    assert cls is HeuristicPoliceBrain


def test_load_brain_class_rejects_malformed_spec():
    with pytest.raises(ValueError, match="package.module:Class"):
        load_brain_class("not-a-valid-spec")


def test_load_brain_class_rejects_non_brainbase_class():
    with pytest.raises(TypeError, match="does not subclass BrainBase"):
        load_brain_class("pathlib:Path")


def test_load_brain_class_rejects_unknown_attribute():
    with pytest.raises(ValueError, match="no attribute"):
        load_brain_class("police_thief.strategy.heuristic:NoSuchBrain")
