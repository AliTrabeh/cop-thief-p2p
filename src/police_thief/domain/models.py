"""Core deterministic domain value types: roles, moves, and board coordinates.

The shared game config shape (mirroring ``config/game.json`` field-for-field,
docs/protocol.md §5) lives in the sibling module ``domain/game_config.py`` —
split out to keep each file under the project's 150-line-per-file limit.
Parsing config files (I/O) lives in ``police_thief.config`` (Part 3); neither
of these two modules does any I/O itself (NFR-001).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class _StrictConfigModel(BaseModel):
    """Base for every ``config/game.json``-shaped model (``domain/game_config.py``,
    ``domain/rate_limiter_config.py``): an unrecognized field (typo'd key,
    stale/renamed parameter) fails loudly at load time instead of being
    silently ignored (PRD-0570).
    """

    model_config = ConfigDict(extra="forbid")


class Role(StrEnum):
    """Which side of the game this peer is playing."""

    POLICE = "police"
    THIEF = "thief"


class Direction(StrEnum):
    """The fixed movement vocabulary (FR-014): 4 orthogonal directions + STAY.

    Diagonal movement does not exist as a value here at all (assumptions.md A-010)
    — it is not merely rejected at runtime, it cannot be constructed.
    """

    NORTH = "N"
    SOUTH = "S"
    EAST = "E"
    WEST = "W"
    STAY = "STAY"


_DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.NORTH: (-1, 0),
    Direction.SOUTH: (1, 0),
    Direction.EAST: (0, 1),
    Direction.WEST: (0, -1),
    Direction.STAY: (0, 0),
}


class Coordinate(BaseModel):
    """A board cell. ``axis_origin_corner = "top-left"``, ``axis_start_index = 0``:
    row 0 is the top row, col 0 is the left column, NORTH decreases row.
    """

    model_config = ConfigDict(frozen=True)

    row: int
    col: int

    def translated(self, direction: Direction) -> Coordinate:
        dr, dc = _DELTAS[direction]
        return Coordinate(row=self.row + dr, col=self.col + dc)

    def manhattan_distance(self, other: Coordinate) -> int:
        return abs(self.row - other.row) + abs(self.col - other.col)
