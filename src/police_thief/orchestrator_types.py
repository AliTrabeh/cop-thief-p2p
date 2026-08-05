"""Small shared types and pure helper functions used by ``orchestrator.py`` and
``orchestrator_messages.py`` — split out to keep each of those files under the
project's 150-line-per-file limit. No behavior here, just the data shapes and
string (de)serialization the two sibling modules share.
"""

from __future__ import annotations

from dataclasses import dataclass

from police_thief.domain.board import BoardState
from police_thief.domain.models import Coordinate, Direction, Role
from police_thief.strategy.base import Action, MoveAction


def action_to_move_str(action: Action) -> str:
    if isinstance(action, MoveAction):
        return f"MOVE:{action.direction.value}"
    return f"BARRIER:{action.coord.row}:{action.coord.col}"


def direction_from_move_str(move_str: str) -> Direction:
    return Direction(move_str.removeprefix("MOVE:"))


def barrier_coord_from_move_str(move_str: str) -> Coordinate:
    _, row_str, col_str = move_str.split(":")
    return Coordinate(row=int(row_str), col=int(col_str))


def opponent_of(role: Role) -> Role:
    return Role.THIEF if role is Role.POLICE else Role.POLICE


def canonical_board_snapshot(board: BoardState) -> str:
    """A stable textual snapshot used as the crypto commitment's ``State``
    component, preventing a move from being replayed against a stale turn.
    """
    barrier_list = sorted((c.row, c.col) for c in board.barriers)
    return (
        f"cop={board.cop_position.row},{board.cop_position.col};"
        f"thief={board.thief_position.row},{board.thief_position.col};"
        f"barriers={barrier_list};moves={board.moves_made}"
    )


@dataclass
class LogEntry:
    """One committed-then-revealed action; ``nonce`` is filled in only at
    end-of-game (FINAL_REVEAL), matching the book's own timing (§5.3.2).
    ``hint`` is the verbal bluff text sent in the Reveal step (spec §5.3.2).
    """

    turn_number: int
    role: Role
    state_hash: str
    move: str
    intent: str
    h_commit: str
    nonce: str | None = None
    hint: str = ""


@dataclass
class PendingOwnTurn:
    action: Action
    entry: LogEntry


class TechnicalLossError(Exception):
    """Raised for a disqualifying violation — ours or the opponent's (FR-021/FR-043)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
