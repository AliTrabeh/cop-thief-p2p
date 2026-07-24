"""Unit tests for domain/board.py — TEST-001 (movement/capture/barrier
mechanics half; config-driven scenarios and config validation live in the
sibling file test_board_config.py, split out to keep each file under 150
lines).
"""

from __future__ import annotations

import pytest

from police_thief.domain.board import BoardState, IllegalActionError, Outcome
from police_thief.domain.models import Coordinate, Direction, Role


def test_initial_positions_from_config(game_config):
    board = BoardState.initial(game_config)
    assert board.cop_position == Coordinate(row=0, col=0)
    assert board.thief_position == Coordinate(row=3, col=3)
    assert board.outcome is Outcome.ONGOING


def test_legal_move_within_bounds(game_config):
    board = BoardState.initial(game_config)
    assert board.is_legal_move(Role.POLICE, Direction.SOUTH)
    board.apply_move(Role.POLICE, Direction.SOUTH)
    assert board.cop_position == Coordinate(row=1, col=0)
    assert board.moves_made == 1


def test_illegal_move_out_of_bounds_north_from_top_row(game_config):
    board = BoardState.initial(game_config)  # cop at (0,0), top-left corner
    assert not board.is_legal_move(Role.POLICE, Direction.NORTH)
    with pytest.raises(IllegalActionError):
        board.apply_move(Role.POLICE, Direction.NORTH)
    assert board.moves_made == 0


def test_illegal_move_out_of_bounds_west_from_left_col(game_config):
    board = BoardState.initial(game_config)
    assert not board.is_legal_move(Role.POLICE, Direction.WEST)


def test_stay_is_always_legal(game_config):
    board = BoardState.initial(game_config)
    assert board.is_legal_move(Role.POLICE, Direction.STAY)
    board.apply_move(Role.POLICE, Direction.STAY)
    assert board.cop_position == Coordinate(row=0, col=0)


def test_move_onto_barrier_is_illegal(game_config):
    board = BoardState.initial(game_config)
    board.barriers.add(Coordinate(row=1, col=0))
    assert not board.is_legal_move(Role.POLICE, Direction.SOUTH)


def test_diagonal_direction_does_not_exist():
    # assumptions.md A-010: diagonal isn't a rejected value, it's not a value at all.
    assert {d.value for d in Direction} == {"N", "S", "E", "W", "STAY"}


def test_capture_by_arrival(game_config):
    board = BoardState.initial(game_config)
    board.thief_position = Coordinate(row=0, col=1)  # adjacent to cop for a 1-move test
    board.apply_move(Role.POLICE, Direction.EAST)
    assert board.outcome is Outcome.CAPTURE
    assert board.cop_position == board.thief_position


def test_barrier_placement_within_manhattan_distance_one(game_config):
    board = BoardState.initial(game_config)
    assert board.can_place_barrier(Coordinate(row=0, col=1))  # adjacent
    assert board.can_place_barrier(Coordinate(row=0, col=0))  # own cell
    assert not board.can_place_barrier(Coordinate(row=2, col=2))  # too far


def test_capture_by_cornering_barrier(game_config):
    board = BoardState.initial(game_config)
    board.thief_position = Coordinate(row=0, col=1)  # adjacent to cop
    board.place_barrier(Coordinate(row=0, col=1))
    assert board.outcome is Outcome.CAPTURE
    assert board.barriers_placed == 1


def test_thief_stranded_when_stay_excluded_and_boxed_in(config_factory):
    # assumptions.md A-013
    base = config_factory()
    cfg = config_factory(
        movement_and_barriers=base.movement_and_barriers.model_copy(
            update={"move_set": [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]}
        ),
    )
    board = BoardState.initial(cfg)
    board.thief_position = Coordinate(row=0, col=0)
    board.cop_position = Coordinate(row=5, col=5)
    # box the thief into corner (0,0) with barriers on both orthogonal neighbors
    board.barriers.add(Coordinate(row=0, col=1))
    board.barriers.add(Coordinate(row=1, col=0))
    # STAY is excluded from this config's move_set, so the cop's own turn must
    # use a real orthogonal move too; this doesn't affect the thief's corner.
    board.apply_move(Role.POLICE, Direction.EAST)
    assert board.legal_moves(Role.THIEF) == []
