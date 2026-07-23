"""Unit tests for domain/scoring.py — FR-020/FR-021."""

from __future__ import annotations

import pytest

from police_thief.domain.board import BoardState, Outcome
from police_thief.domain.models import Direction, Role
from police_thief.domain.scoring import score, technical_loss_score


def test_score_requires_finished_game(game_config):
    board = BoardState.initial(game_config)
    with pytest.raises(ValueError, match="has not ended"):
        score(board)


def test_score_on_capture(game_config):
    board = BoardState.initial(game_config)
    board.outcome = Outcome.CAPTURE
    cop_score, thief_score = score(board)
    assert (cop_score, thief_score) == (20, 5)


def test_score_on_thief_stranded_matches_capture_table(game_config):
    board = BoardState.initial(game_config)
    board.outcome = Outcome.THIEF_STRANDED
    assert score(board) == (20, 5)


def test_score_on_survival(game_config):
    board = BoardState.initial(game_config)
    board.outcome = Outcome.SURVIVAL
    cop_score, thief_score = score(board)
    assert (cop_score, thief_score) == (5, 10)


def test_technical_loss_credits_the_honest_side(game_config):
    # assumptions.md A-014
    dq_cop, dq_thief = technical_loss_score(game_config, Role.POLICE)
    assert dq_cop == 0
    assert dq_thief == game_config.scoring.survival_thief

    ok_cop, ok_thief = technical_loss_score(game_config, Role.THIEF)
    assert ok_cop == game_config.scoring.survival_cop
    assert ok_thief == 0


def test_full_game_capture_scores_correctly(game_config):
    board = BoardState.initial(game_config)
    board.thief_position = board.thief_position.__class__(row=0, col=1)
    board.apply_move(Role.POLICE, Direction.EAST)
    assert board.outcome is Outcome.CAPTURE
    assert score(board) == (20, 5)
