"""Unit tests for domain/board.py — TEST-001 (config-driven scenarios and
config validation half, split out of test_board.py to keep each file under
150 lines).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from police_thief.domain.board import BoardState, IllegalActionError, Outcome
from police_thief.domain.game_config import BoardAndAgentsConfig
from police_thief.domain.models import Coordinate, Direction, Role


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
