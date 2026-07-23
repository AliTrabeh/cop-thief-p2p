"""Unit tests for domain/board.py — TEST-001.

Covers: legal/illegal moves, boundaries, barrier legality, capture by arrival,
capture by cornering, thief-stranded, survival win, and board-vs-config errors.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from police_thief.domain.board import BoardState, IllegalActionError, Outcome
from police_thief.domain.models import BoardAndAgentsConfig, Coordinate, Direction, Role


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


def test_barrier_budget_enforced(game_config, config_factory):
    cfg = config_factory(
        movement_and_barriers=game_config.movement_and_barriers.model_copy(
            update={"max_barriers": 1}
        )
    )
    board = BoardState.initial(cfg)
    board.place_barrier(Coordinate(row=0, col=1))
    assert board.outcome is Outcome.CAPTURE or board.barriers_placed == 1
    # A second, independent board to test budget exhaustion without ending the game:
    board2 = BoardState.initial(cfg)
    board2.place_barrier(Coordinate(row=1, col=0))
    assert not board2.can_place_barrier(Coordinate(row=0, col=1))


def test_survival_win_after_max_moves(game_config, config_factory):
    cfg = config_factory(
        movement_and_barriers=game_config.movement_and_barriers.model_copy(
            update={"max_moves": 2, "survival_threshold": 35}
        )
    )
    board = BoardState.initial(cfg)
    board.apply_move(Role.POLICE, Direction.STAY)
    assert board.outcome == Outcome.ONGOING
    board.apply_move(Role.POLICE, Direction.STAY)
    assert board.outcome == Outcome.SURVIVAL


def test_survival_win_after_thief_survival_threshold(game_config, config_factory):
    cfg = config_factory(
        movement_and_barriers=game_config.movement_and_barriers.model_copy(
            update={"max_moves": 1000, "survival_threshold": 2}
        )
    )
    board = BoardState.initial(cfg)
    board.apply_move(Role.THIEF, Direction.STAY)
    assert board.outcome == Outcome.ONGOING
    board.apply_move(Role.THIEF, Direction.STAY)
    assert board.outcome == Outcome.SURVIVAL


def test_no_moves_after_game_over(game_config, config_factory):
    cfg = config_factory(
        movement_and_barriers=game_config.movement_and_barriers.model_copy(update={"max_moves": 1})
    )
    board = BoardState.initial(cfg)
    board.apply_move(Role.POLICE, Direction.STAY)
    assert board.outcome is Outcome.SURVIVAL
    with pytest.raises(IllegalActionError):
        board.apply_move(Role.POLICE, Direction.STAY)


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


def test_config_rejects_barriers_leaving_no_free_path(config_factory):
    base = config_factory()
    with pytest.raises(ValidationError):
        config_factory(
            board_and_agents=base.board_and_agents.model_copy(update={"grid_size": 7}),
            movement_and_barriers=base.movement_and_barriers.model_copy(
                update={"max_barriers": 48}  # 7*7-2=47 free cells; 48 leaves no path
            ),
        )


def test_config_rejects_out_of_bounds_start_position(config_factory):
    base = config_factory()
    with pytest.raises(ValidationError):
        config_factory(
            board_and_agents=base.board_and_agents.model_copy(update={"thief_start": (99, 99)})
        )


def test_config_rejects_coinciding_start_positions(config_factory):
    base = config_factory()
    with pytest.raises(ValidationError):
        config_factory(
            board_and_agents=base.board_and_agents.model_copy(update={"thief_start": (0, 0)})
        )


def test_config_rejects_sub_minimum_board_size():
    with pytest.raises(ValidationError):
        BoardAndAgentsConfig(grid_size=5, thief_start=(3, 3), cop_start=(0, 0))
