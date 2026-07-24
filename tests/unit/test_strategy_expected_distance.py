"""Unit tests for the expected-distance-over-belief upgrade in
strategy/heuristic.py (split out of test_strategy.py to keep each file
under 150 lines) — the specific fixes over the old plain-argmax heuristic:
center-seeking under uniform belief, confidence-gated barrier placement,
and the thief's interior-mobility tie-break.
"""

from __future__ import annotations

from police_thief.domain.board import BoardState
from police_thief.domain.models import Coordinate, Role
from police_thief.domain.scent import ScentField
from police_thief.strategy.base import BarrierAction, MoveAction, build_belief_view
from police_thief.strategy.heuristic import HeuristicPoliceBrain, HeuristicThiefBrain


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
